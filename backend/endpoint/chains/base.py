from __future__ import annotations

from typing import Protocol

from endpoint.models import Transfer


class ChainAdapter(Protocol):
    """Chain-neutral boundary used by investigation services."""

    chain: str

    async def get_address_transfers(
        self, address: str, signature_limit: int
    ) -> tuple[list[Transfer], int]: ...
