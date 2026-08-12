from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from endpoint.analysis import build_graph
from endpoint.chains.base import ChainAdapter
from endpoint.demo import synthetic_demo_transfers
from endpoint.models import InvestigationGraph, TraceLimits, Transfer
from endpoint.repository import InvestigationRepository


class InvestigationService:
    def __init__(
        self,
        adapter: ChainAdapter,
        repository: InvestigationRepository,
        rpc_url: str,
    ) -> None:
        self.adapter = adapter
        self.repository = repository
        self.rpc_url = rpc_url

    async def trace(
        self, address: str, signature_limit: int, name: str | None
    ) -> InvestigationGraph:
        transfers, returned = await self.adapter.get_address_transfers(address, signature_limit)
        nodes, edges, evidence, candidates = build_graph(address, transfers, self.rpc_url)
        now = datetime.now(UTC)
        investigation_id = "inv_" + hashlib.sha256(
            f"solana:{address}:{now.isoformat()}".encode()
        ).hexdigest()[:16]
        graph = InvestigationGraph(
            investigation_id=investigation_id,
            name=name or f"Solana trace {address[:6]}…{address[-4:]}",
            seed=address,
            data_source="live_rpc",
            created_at=now,
            nodes=nodes,
            edges=edges,
            evidence=evidence,
            exit_candidates=candidates,
            limits=TraceLimits(
                requested_signatures=signature_limit,
                returned_signatures=returned,
                truncated=returned >= signature_limit,
                notice=(
                    "The RPC signature limit was reached; this investigation is incomplete."
                    if returned >= signature_limit
                    else None
                ),
            ),
        )
        self.repository.save(graph)
        return graph

    def demo(self) -> InvestigationGraph:
        seed, transfers = synthetic_demo_transfers()
        nodes, edges, evidence, candidates = build_graph(seed, transfers)
        graph = InvestigationGraph(
            investigation_id="demo_synthetic_rug_flow",
            name="Synthetic rug-flow demonstration",
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
        return graph

    async def expand(
        self, investigation_id: str, address: str, signature_limit: int
    ) -> InvestigationGraph | None:
        existing = self.repository.get(investigation_id)
        if existing is None:
            return None
        if existing.data_source != "live_rpc":
            raise ValueError("Synthetic demonstrations cannot be expanded with live RPC data")
        new_transfers, returned = await self.adapter.get_address_transfers(address, signature_limit)
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
                decimals=9 if item.asset == "SOL" else 0,
                kind="native_transfer" if item.asset == "SOL" else "token_transfer",
                instruction_path=item.instruction_path,
            )
            for item in existing.evidence
        ]
        merged = {transfer.id: transfer for transfer in [*old_transfers, *new_transfers]}
        nodes, edges, evidence, candidates = build_graph(
            existing.seed, list(merged.values()), self.rpc_url
        )
        existing.nodes = nodes
        existing.edges = edges
        existing.evidence = evidence
        existing.exit_candidates = candidates
        existing.limits = TraceLimits(
            requested_signatures=existing.limits.requested_signatures + signature_limit,
            returned_signatures=existing.limits.returned_signatures + returned,
            truncated=existing.limits.truncated or returned >= signature_limit,
            notice=(
                "At least one RPC signature limit was reached; this investigation is incomplete."
                if existing.limits.truncated or returned >= signature_limit
                else None
            ),
        )
        self.repository.save(existing)
        return existing
