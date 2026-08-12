from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from endpoint.models import Transfer


@dataclass(frozen=True, slots=True)
class TransferFetchResult:
    """Chain-neutral result for a bounded transaction-history request."""

    transfers: list[Transfer]
    signatures_seen: int
    transactions_processed: int
    transactions_failed: int


class ChainAdapter(Protocol):
    """Chain-neutral boundary used by investigation services."""

    chain: str

    async def get_address_transfers(
        self, address: str, signature_limit: int
    ) -> TransferFetchResult: ...
