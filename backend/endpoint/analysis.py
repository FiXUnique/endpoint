from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import combinations

from endpoint.models import (
    AssetTotal,
    Certainty,
    EvidenceRef,
    ExitCandidate,
    GraphEdge,
    GraphNode,
    Signal,
    Transfer,
)

NATIVE_DUST_CUTOFF = Decimal("0.00001")


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def _score_label(score: float) -> str:
    if score >= 0.8:
        return "strong evidence score"
    if score >= 0.55:
        return "moderate evidence score"
    return "weak evidence score"


def _seconds_between(left: datetime | None, right: datetime | None) -> float | None:
    if left is None or right is None:
        return None
    return abs((left - right).total_seconds())


def _is_probable_noise(transfer: Transfer) -> bool:
    """Identify negligible native transfers commonly used for address poisoning.

    The evidence remains visible and exportable. The flag only prevents tiny transfers
    from dominating relationship and endpoint ranking.
    """
    return (
        transfer.kind == "native_transfer"
        and Decimal(transfer.amount) <= NATIVE_DUST_CUTOFF
    )


def _asset_totals(transfers: list[Transfer]) -> list[AssetTotal]:
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    for transfer in transfers:
        totals[transfer.asset] += Decimal(transfer.amount)
    return [
        AssetTotal(asset=asset, amount=format(amount, "f"))
        for asset, amount in sorted(totals.items())
    ]


def _hop_distances(seed: str, transfers: list[Transfer]) -> dict[str, int]:
    destinations: defaultdict[str, set[str]] = defaultdict(set)
    for transfer in transfers:
        destinations[transfer.source].add(transfer.target)
    distances = {seed: 0}
    frontier = [seed]
    while frontier:
        source = frontier.pop(0)
        for target in destinations[source]:
            if target not in distances:
                distances[target] = distances[source] + 1
                frontier.append(target)
    return distances


def build_graph(
    seed: str,
    transfers: list[Transfer],
    rpc_url: str | None = None,
    chain: str = "solana",
) -> tuple[list[GraphNode], list[GraphEdge], list[EvidenceRef], list[ExitCandidate]]:
    """Build a compact evidence graph without inventing relationships.

    Direct transfer edges are confirmed facts. Common-funder edges are heuristics
    whose contribution formula is versioned and described in docs/methodology.md.
    """
    evidence = [
        EvidenceRef(
            id=transfer.id,
            chain=chain,
            signature=transfer.signature,
            slot=transfer.slot,
            timestamp=transfer.timestamp,
            source=transfer.source,
            target=transfer.target,
            asset=transfer.asset,
            amount=transfer.amount,
            instruction_path=transfer.instruction_path,
            rpc_url=rpc_url,
        )
        for transfer in transfers
    ]

    addresses = {seed}
    incoming: defaultdict[str, int] = defaultdict(int)
    outgoing: defaultdict[str, int] = defaultdict(int)
    assets: defaultdict[str, set[str]] = defaultdict(set)
    grouped: defaultdict[tuple[str, str, str], list[Transfer]] = defaultdict(list)
    for transfer in transfers:
        addresses.update((transfer.source, transfer.target))
        outgoing[transfer.source] += 1
        incoming[transfer.target] += 1
        assets[transfer.source].add(transfer.asset)
        assets[transfer.target].add(transfer.asset)
        grouped[(transfer.source, transfer.target, transfer.asset)].append(transfer)

    nodes = [
        GraphNode(
            id=address,
            address=address,
            seed=address == seed,
            incoming_count=incoming[address],
            outgoing_count=outgoing[address],
            observed_assets=sorted(assets[address]),
        )
        for address in sorted(addresses)
    ]

    edges: list[GraphEdge] = []
    for (source, target, asset), group in sorted(grouped.items()):
        total = sum(Decimal(transfer.amount) for transfer in group)
        ids = [transfer.id for transfer in group]
        edges.append(
            GraphEdge(
                id=f"edge_{_short_hash(f'{source}:{target}:{asset}')}",
                source=source,
                target=target,
                relationship="observed_transfer",
                certainty=Certainty.CONFIRMED,
                evidence_score=1,
                label=f"{format(total, 'f')} {asset}",
                asset=asset,
                amount=format(total, "f"),
                transfer_count=len(group),
                signals=[
                    Signal(
                        type="on_chain_transfer",
                        contribution=1,
                        explanation=(
                            f"{len(group)} parsed on-chain transfer"
                            f"{'s' if len(group) != 1 else ''}"
                        ),
                        evidence_ids=ids,
                    )
                ],
                evidence_ids=ids,
                probable_noise=all(_is_probable_noise(transfer) for transfer in group),
            )
        )

    meaningful_transfers = [transfer for transfer in transfers if not _is_probable_noise(transfer)]
    by_funder: defaultdict[str, defaultdict[str, list[Transfer]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for transfer in meaningful_transfers:
        by_funder[transfer.source][transfer.target].append(transfer)

    for funder, recipients in sorted(by_funder.items()):
        if len(recipients) < 2:
            continue
        for left, right in combinations(sorted(recipients), 2):
            left_transfers = recipients[left]
            right_transfers = recipients[right]
            relevant = [*left_transfers, *right_transfers]
            signals = [
                Signal(
                    type="common_funder",
                    contribution=0.45,
                    explanation=f"Both addresses received observed transfers from {funder}",
                    evidence_ids=[transfer.id for transfer in relevant],
                )
            ]
            contribution = 0.45
            deltas = [
                delta
                for a in left_transfers
                for b in right_transfers
                if (delta := _seconds_between(a.timestamp, b.timestamp)) is not None
            ]
            if deltas and min(deltas) <= 120:
                timing_contribution = round(0.2 * (1 - min(deltas) / 120), 4)
                contribution += timing_contribution
                signals.append(
                    Signal(
                        type="temporal_proximity",
                        contribution=timing_contribution,
                        explanation=(
                            f"Funding events were {round(min(deltas))} seconds apart "
                            "inside the configured 120-second window"
                        ),
                        evidence_ids=[transfer.id for transfer in relevant],
                    )
                )
            score = round(min(contribution, 1), 4)
            relationship_id = _short_hash(f"related:{left}:{right}:{funder}")
            edges.append(
                GraphEdge(
                    id=f"rel_{relationship_id}",
                    source=left,
                    target=right,
                    relationship="possible_common_funding_cluster",
                    certainty=Certainty.HEURISTIC,
                    evidence_score=score,
                    label=_score_label(score),
                    signals=signals,
                    evidence_ids=sorted({item.id for item in relevant}),
                )
            )

    candidates: list[ExitCandidate] = []
    distances = _hop_distances(seed, meaningful_transfers)
    reachable = set(distances)
    relevant = [
        transfer
        for transfer in meaningful_transfers
        if transfer.source in reachable and transfer.target in reachable
    ]
    incoming_by_target: defaultdict[str, list[Transfer]] = defaultdict(list)
    outgoing_by_source: defaultdict[str, list[Transfer]] = defaultdict(list)
    maximum_received_by_asset: defaultdict[str, Decimal] = defaultdict(Decimal)
    for transfer in relevant:
        incoming_by_target[transfer.target].append(transfer)
        outgoing_by_source[transfer.source].append(transfer)
    for target, target_transfers in incoming_by_target.items():
        if target == seed:
            continue
        for total in _asset_totals(target_transfers):
            maximum_received_by_asset[total.asset] = max(
                maximum_received_by_asset[total.asset], Decimal(total.amount)
            )

    for target, target_transfers in incoming_by_target.items():
        if target == seed:
            continue
        sources = {transfer.source for transfer in target_transfers}
        target_outgoing = outgoing_by_source[target]
        received_assets = _asset_totals(target_transfers)
        prominence = max(
            (
                Decimal(total.amount) / maximum_received_by_asset[total.asset]
                for total in received_assets
                if maximum_received_by_asset[total.asset]
            ),
            default=Decimal(0),
        )
        direct = any(transfer.source == seed for transfer in target_transfers)
        terminal = not target_outgoing
        repeat_signal = min(len(target_transfers) / 3, 1)
        asset_signal = min(len(received_assets) / 2, 1)
        score = (
            (0.25 if terminal else 0)
            + (0.2 if direct else 0)
            + 0.2 * repeat_signal
            + 0.25 * float(prominence)
            + 0.1 * asset_signal
        )
        score = round(min(score, 0.95), 4)
        asset_summary = ", ".join(
            f"{total.amount} {total.asset}" for total in received_assets
        )
        terminal_summary = (
            "No meaningful outgoing transfer was observed in this snapshot."
            if terminal
            else f"{len(target_outgoing)} meaningful outgoing transfer(s) were also observed."
        )
        candidates.append(
            ExitCandidate(
                address=target,
                evidence_score=score,
                label="likely observed endpoint" if terminal else "fund-flow waypoint",
                explanation=(
                    f"Received {asset_summary} across "
                    f"{len(target_transfers)} meaningful transfer(s). "
                    f"{terminal_summary} This identifies where the observed trail stops, not who "
                    "controls the wallet; it is not an attribution or proof of off-ramping."
                ),
                contributing_wallets=len(sources),
                evidence_ids=sorted({transfer.id for transfer in target_transfers}),
                direct_from_seed=direct,
                terminal_in_observed_graph=terminal,
                hop_distance=distances[target],
                incoming_transfer_count=len(target_transfers),
                outgoing_transfer_count=len(target_outgoing),
                received_assets=received_assets,
            )
        )
    candidates.sort(
        key=lambda item: (
            not item.terminal_in_observed_graph,
            -item.evidence_score,
            item.hop_distance or 0,
            item.address,
        )
    )
    return nodes, edges, evidence, candidates
