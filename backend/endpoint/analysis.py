from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import combinations

from endpoint.models import (
    Certainty,
    EvidenceRef,
    ExitCandidate,
    GraphEdge,
    GraphNode,
    Signal,
    Transfer,
)


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


def build_graph(
    seed: str, transfers: list[Transfer], rpc_url: str | None = None
) -> tuple[list[GraphNode], list[GraphEdge], list[EvidenceRef], list[ExitCandidate]]:
    """Build a compact evidence graph without inventing relationships.

    Direct transfer edges are confirmed facts. Common-funder edges are heuristics
    whose contribution formula is versioned and described in docs/methodology.md.
    """
    evidence = [
        EvidenceRef(
            id=transfer.id,
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
            )
        )

    by_funder: defaultdict[str, defaultdict[str, list[Transfer]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for transfer in transfers:
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
    incoming_sources: defaultdict[str, set[str]] = defaultdict(set)
    incoming_evidence: defaultdict[str, list[str]] = defaultdict(list)
    for transfer in transfers:
        incoming_sources[transfer.target].add(transfer.source)
        incoming_evidence[transfer.target].append(transfer.id)
    maximum_sources = max((len(sources) for sources in incoming_sources.values()), default=1)
    for target, sources in incoming_sources.items():
        if len(sources) < 2 or target == seed:
            continue
        convergence = min(len(sources) / max(maximum_sources, 2), 1)
        score = round(0.3 + 0.5 * convergence, 4)
        candidates.append(
            ExitCandidate(
                address=target,
                evidence_score=score,
                label="potential consolidation point",
                explanation=(
                    f"Received observed transfers from {len(sources)} distinct graph addresses. "
                    "This is a convergence heuristic, not an attribution or proof of off-ramping."
                ),
                contributing_wallets=len(sources),
                evidence_ids=sorted(set(incoming_evidence[target])),
            )
        )
    candidates.sort(
        key=lambda item: (-item.evidence_score, -item.contributing_wallets, item.address)
    )
    return nodes, edges, evidence, candidates
