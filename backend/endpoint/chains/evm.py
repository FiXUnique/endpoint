from __future__ import annotations

import asyncio
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from endpoint.chains.base import TransferFetchResult
from endpoint.models import Transfer

EVM_NETWORKS: dict[str, dict[str, str]] = {
    "ethereum": {"name": "Ethereum", "chain_id": "1", "native_asset": "ETH"},
    "base": {"name": "Base", "chain_id": "8453", "native_asset": "ETH"},
    "bnb": {"name": "BNB Smart Chain", "chain_id": "56", "native_asset": "BNB"},
    "polygon": {"name": "Polygon", "chain_id": "137", "native_asset": "POL"},
    "arbitrum": {"name": "Arbitrum One", "chain_id": "42161", "native_asset": "ETH"},
    "optimism": {"name": "Optimism", "chain_id": "10", "native_asset": "ETH"},
    "avalanche": {"name": "Avalanche C-Chain", "chain_id": "43114", "native_asset": "AVAX"},
}


class EvmIndexerError(RuntimeError):
    """Raised when the public EVM indexer cannot return a usable response."""

    def __init__(
        self, message: str, *, code: str = "evm_indexer_error", retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class EvmAdapter:
    def __init__(
        self,
        chain: str,
        *,
        base_url: str = "https://api.routescan.io/v2/network/mainnet/evm",
        api_key: str | None = None,
        timeout: float = 20,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if chain not in EVM_NETWORKS:
            raise ValueError(f"Unsupported EVM network: {chain}")
        network = EVM_NETWORKS[chain]
        self.chain = chain
        self.display_name = network["name"]
        self.native_asset = network["native_asset"]
        self.chain_id = network["chain_id"]
        self.base_url = base_url.rstrip("/")
        self.source_url = f"{self.base_url}/{self.chain_id}"
        self.api_key = api_key
        self._max_retries = max(max_retries, 0)
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "Endpoint-Forensics/0.2"},
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(self, path: str, limit: int) -> list[dict[str, Any]]:
        params: dict[str, str | int | bool] = {"sort": "desc", "limit": limit}
        if path == "erc20-transfers":
            params["excludeZeroValue"] = True
        if self.api_key:
            params["apikey"] = self.api_key
        url = f"{self.source_url}/{path}"
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(url, params=params)
            except httpx.HTTPError as exc:
                if attempt < self._max_retries:
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                raise EvmIndexerError(
                    f"{self.display_name} history service could not be reached.",
                    code="evm_transport_error",
                    retryable=True,
                ) from exc
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self._max_retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 0.5 * (attempt + 1)
                    )
                    await asyncio.sleep(min(delay, 4))
                    continue
                raise EvmIndexerError(
                    f"{self.display_name} history service is temporarily rate-limited.",
                    code="evm_rate_limited",
                    retryable=True,
                )
            if response.status_code >= 400:
                raise EvmIndexerError(
                    f"{self.display_name} history service returned HTTP {response.status_code}.",
                    code="evm_indexer_response_error",
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise EvmIndexerError(
                    f"{self.display_name} history service returned invalid JSON.",
                    code="evm_invalid_response",
                ) from exc
            items = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                raise EvmIndexerError(
                    f"{self.display_name} history service returned an unexpected response.",
                    code="evm_invalid_response",
                )
            return [item for item in items if isinstance(item, dict)]
        return []

    async def get_address_transfers(
        self, address: str, signature_limit: int
    ) -> TransferFetchResult:
        normalized_address = address.lower()
        prefix = f"address/{normalized_address}"
        normal_items, token_items = await asyncio.gather(
            self._get(f"{prefix}/transactions", signature_limit),
            self._get(f"{prefix}/erc20-transfers", signature_limit),
        )
        transfers = [
            *self.normalize_native_transactions(normal_items),
            *self.normalize_token_transfers(token_items),
        ]
        transfers.sort(
            key=lambda item: item.timestamp.timestamp() if item.timestamp else 0,
            reverse=True,
        )
        permitted_signatures: list[str] = []
        for transfer in transfers:
            if transfer.signature not in permitted_signatures:
                permitted_signatures.append(transfer.signature)
            if len(permitted_signatures) >= signature_limit:
                break
        allowed = set(permitted_signatures)
        bounded = [item for item in transfers if item.signature in allowed]
        raw_signatures = {
            str(item.get("id") or item.get("txHash"))
            for item in [*normal_items, *token_items]
            if item.get("id") or item.get("txHash")
        }
        return TransferFetchResult(
            transfers=bounded,
            signatures_seen=min(len(raw_signatures), signature_limit),
            transactions_processed=min(len(raw_signatures), signature_limit),
            transactions_failed=0,
        )

    def normalize_native_transactions(self, items: list[dict[str, Any]]) -> list[Transfer]:
        transfers: list[Transfer] = []
        for item in items:
            if item.get("status") is False:
                continue
            source = item.get("from")
            target = item.get("to")
            signature = item.get("id") or item.get("txHash")
            raw_value = item.get("value")
            if not source or not target or not signature or raw_value is None:
                continue
            amount = Decimal(str(raw_value)) / Decimal(10**18)
            if amount <= 0:
                continue
            transfers.append(
                Transfer(
                    id=f"evm:{self.chain_id}:{signature}:native",
                    signature=str(signature),
                    slot=int(item.get("blockNumber") or 0),
                    timestamp=_timestamp(item.get("timestamp")),
                    source=str(source).lower(),
                    target=str(target).lower(),
                    asset=self.native_asset,
                    amount=format(amount, "f"),
                    decimals=18,
                    kind="native_transfer",
                    instruction_path="evm:transaction:value",
                )
            )
        return transfers

    def normalize_token_transfers(self, items: list[dict[str, Any]]) -> list[Transfer]:
        transfers: list[Transfer] = []
        for item in items:
            source = item.get("from")
            target = item.get("to")
            signature = item.get("txHash") or item.get("id")
            raw_amount = item.get("amount")
            if not source or not target or not signature or raw_amount is None:
                continue
            decimals = int(item.get("tokenDecimals") or 0)
            amount = Decimal(str(raw_amount)) / (Decimal(10) ** decimals)
            if amount <= 0:
                continue
            token_address = str(item.get("tokenAddress") or "ERC20").lower()
            symbol = str(item.get("tokenSymbol") or "").strip()
            asset = (
                symbol
                if re.fullmatch(r"[A-Za-z0-9._-]{1,18}", symbol)
                else token_address
            )
            log_index = item.get("logIndex", 0)
            transfers.append(
                Transfer(
                    id=f"evm:{self.chain_id}:{signature}:log:{log_index}",
                    signature=str(signature),
                    slot=int(item.get("blockNumber") or 0),
                    timestamp=_timestamp(item.get("timestamp") or item.get("createdAt")),
                    source=str(source).lower(),
                    target=str(target).lower(),
                    asset=asset,
                    amount=format(amount, "f"),
                    decimals=decimals,
                    kind="token_transfer",
                    instruction_path=f"evm:erc20:log:{log_index}:{token_address}",
                )
            )
        return transfers


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
