from __future__ import annotations

from datetime import UTC, datetime, timedelta

from endpoint.models import Transfer


def synthetic_demo_transfers() -> tuple[str, list[Transfer]]:
    """Transparent fixture for demonstrations; never used by live analysis paths."""
    seed = "RugSeedWallet11111111111111111111111111111"
    wallet_a = "SplitWalletA11111111111111111111111111111"
    wallet_b = "SplitWalletB11111111111111111111111111111"
    wallet_c = "SplitWalletC11111111111111111111111111111"
    consolidation = "Consolidate1111111111111111111111111111"
    service = "KnownService1111111111111111111111111111"
    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    paths = [
        (seed, wallet_a, "18.5", 0),
        (seed, wallet_b, "16.0", 22),
        (seed, wallet_c, "15.5", 51),
        (wallet_a, consolidation, "18.0", 300),
        (wallet_b, consolidation, "15.7", 318),
        (wallet_c, consolidation, "15.1", 342),
        (consolidation, service, "47.9", 900),
    ]
    transfers = []
    for index, (source, target, amount, offset) in enumerate(paths):
        transfers.append(
            Transfer(
                id=f"demo_evidence_{index + 1}",
                signature=f"SyntheticSignature{index + 1:02d}NotOnChain",
                slot=300_000_000 + index,
                timestamp=base + timedelta(seconds=offset),
                source=source,
                target=target,
                asset="SOL",
                amount=amount,
                decimals=9,
                kind="native_transfer",
                instruction_path=f"synthetic:{index}",
            )
        )
    return seed, transfers
