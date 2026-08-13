from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from endpoint.analysis import build_graph
from endpoint.chains.base import ChainAdapter, TransferFetchResult
from endpoint.demo import synthetic_demo_transfers
from endpoint.models import (
    InvestigationGraph,
    TraceLimits,
    Transfer,
    validate_chain_address,
)
from endpoint.repository import InvestigationRepository


class InvestigationService:
    def __init__(
        self,
        adapters: dict[str, ChainAdapter],
        repository: InvestigationRepository,
    ) -> None:
        self.adapters = adapters
        self.repository = repository

    async def trace(
        self,
        chain: str,
        address: str,
        signature_limit: int,
        name: str | None,
    ) -> InvestigationGraph:
        adapter = self.adapters[chain]
        address = validate_chain_address(chain, address)
        result = await adapter.get_address_transfers(address, signature_limit)
        nodes, edges, evidence, candidates = build_graph(
            address,
            result.transfers,
            adapter.source_url,
            chain,
        )
        now = datetime.now(UTC)
        investigation_id = "inv_" + hashlib.sha256(
            f"{chain}:{address}:{now.isoformat()}".encode()
        ).hexdigest()[:16]
        graph = InvestigationGraph(
            investigation_id=investigation_id,
            name=name or f"{adapter.display_name} trace {address[:6]}…{address[-4:]}",
            chain=chain,
            seed=address,
            data_source="live_rpc" if chain == "solana" else "live_indexer",
            created_at=now,
            nodes=nodes,
            edges=edges,
            evidence=evidence,
            exit_candidates=candidates,
            limits=TraceLimits(
                requested_signatures=signature_limit,
                returned_signatures=result.signatures_seen,
                processed_transactions=result.transactions_processed,
                failed_transactions=result.transactions_failed,
                truncated=result.signatures_seen >= signature_limit,
                notice=self._notice(result, signature_limit, adapter.display_name),
            ),
        )
        self.repository.save(graph)
        return graph

    def demo(self) -> InvestigationGraph:
        seed, transfers = synthetic_demo_transfers()
        nodes, edges, evidence, candidates = build_graph(
            seed, transfers, chain="solana"
        )
        return InvestigationGraph(
            investigation_id="demo_synthetic_rug_flow",
            name="Synthetic rug-flow demonstration",
            chain="solana",
            seed=seed,
            data_source="synthetic_demo",
            nodes=nodes,
            edges=edges,
            evidence=evidence,
            exit_candidates=candidates,
            limits=TraceLimits(
                requested_signatures=0,
                returned_signatures=0,
                truncated=False,
                notice="Synthetic fixture: addresses and signatures are not real on-chain data.",
            ),
        )

    async def expand(
        self, investigation_id: str, address: str, signature_limit: int
    ) -> InvestigationGraph | None:
        existing = self.repository.get(investigation_id)
        if existing is None:
            return None
        if existing.data_source == "synthetic_demo":
            raise ValueError("Synthetic demonstrations cannot be expanded with live data")
        adapter = self.adapters[existing.chain]
        address = validate_chain_address(existing.chain, address)
        result = await adapter.get_address_transfers(address, signature_limit)
        old_transfers = [
            Transfer(
                id=item.id,
                signature=item.signature,
                slot=item.slot,
                timestamp=item.timestamp,
                source=item.source,
                target=item.target,
                asset=item.asset,
                amount=item.amount,
                decimals=(
                    9
                    if item.asset == "SOL"
                    else 18
                    if item.asset == adapter.native_asset
                    else 0
                ),
                kind=(
                    "native_transfer"
                    if item.asset == adapter.native_asset
                    else "token_transfer"
                ),
                instruction_path=item.instruction_path,
            )
            for item in existing.evidence
        ]
        merged = {
            transfer.id: transfer for transfer in [*old_transfers, *result.transfers]
        }
        nodes, edges, evidence, candidates = build_graph(
            existing.seed,
            list(merged.values()),
            adapter.source_url,
            existing.chain,
        )
        existing.nodes = nodes
        existing.edges = edges
        existing.evidence = evidence
        existing.exit_candidates = candidates
        existing.limits = TraceLimits(
            requested_signatures=existing.limits.requested_signatures + signature_limit,
            returned_signatures=(
                existing.limits.returned_signatures + result.signatures_seen
            ),
            processed_transactions=(
                existing.limits.processed_transactions + result.transactions_processed
            ),
            failed_transactions=(
                existing.limits.failed_transactions + result.transactions_failed
            ),
            truncated=existing.limits.truncated or result.signatures_seen >= signature_limit,
            notice=self._notice(
                TransferFetchResult(
                    transfers=result.transfers,
                    signatures_seen=(
                        existing.limits.returned_signatures + result.signatures_seen
                    ),
                    transactions_processed=(
                        existing.limits.processed_transactions
                        + result.transactions_processed
                    ),
                    transactions_failed=(
                        existing.limits.failed_transactions + result.transactions_failed
                    ),
                ),
                existing.limits.requested_signatures + signature_limit,
                adapter.display_name,
                prefix="Expanded investigation. ",
            ),
        )
        self.repository.save(existing)
        return existing

    @staticmethod
    def _notice(
        result: TransferFetchResult,
        signature_limit: int,
        network_name: str,
        prefix: str = "",
    ) -> str | None:
        notices: list[str] = []
        if result.signatures_seen >= signature_limit:
            notices.append(
                "The transaction limit was reached; older activity is not included."
            )
        if result.transactions_failed:
            notices.append(
                f"{result.transactions_failed} transaction"
                f"{'s were' if result.transactions_failed != 1 else ' was'} unavailable "
                "after retries; results are partial."
            )
        if result.transactions_processed and not result.transfers:
            notices.append(
                f"Transactions were inspected on {network_name}, but no supported positive-value "
                "native or token transfers were present in this slice."
            )
        if not result.signatures_seen:
            notices.append(
                f"No indexed transactions were found for this address on {network_name}. "
                "EVM addresses can exist on multiple networks; select another network if needed."
            )
        return prefix + " ".join(notices) if notices else None
