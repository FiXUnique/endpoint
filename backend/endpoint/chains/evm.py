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
    "ethereum": {
        "name": "Ethereum",
        "chain_id": "1",
        "native_asset": "ETH",
        "provider": "routescan",
    },
    "base": {"name": "Base", "chain_id": "8453", "native_asset": "ETH", "provider": "routescan"},
    "bnb": {
        "name": "BNB Smart Chain",
        "chain_id": "56",
        "native_asset": "BNB",
        "provider": "three_xpl",
        "api_url": "https://api.3xpl.com/bnb",
    },
    "polygon": {
        "name": "Polygon",
        "chain_id": "137",
        "native_asset": "POL",
        "provider": "routescan",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": "42161",
        "native_asset": "ETH",
        "provider": "routescan",
    },
    "optimism": {
        "name": "Optimism",
        "chain_id": "10",
        "native_asset": "ETH",
        "provider": "routescan",
    },
    "avalanche": {
        "name": "Avalanche C-Chain",
        "chain_id": "43114",
        "native_asset": "AVAX",
        "provider": "routescan",
    },
    "robinhood": {
        "name": "Robinhood Chain",
        "chain_id": "4663",
        "native_asset": "ETH",
        "provider": "blockscout",
        "api_url": "https://robinhoodchain.blockscout.com/api/v2",
    },
}

THREE_XPL_PUBLIC_TOKEN = "3A0_t3st3xplor3rpub11cb3t4efcd21748a5e"


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
        self.provider = network["provider"]
        self.base_url = base_url.rstrip("/")
        self.source_url = (
            f"{self.base_url}/{self.chain_id}"
            if self.provider == "routescan"
            else network["api_url"].rstrip("/")
        )
        self.api_key = api_key
        self._max_retries = max(max_retries, 0)
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
                ),
            },
        )
        if self.provider == "blockscout":
            self._client.headers["Referer"] = "https://robinhoodchain.blockscout.com/"
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request_json(self, url: str, params: dict[str, str | int | bool]) -> dict[str, Any]:
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
            if not isinstance(payload, dict):
                raise EvmIndexerError(
                    f"{self.display_name} history service returned an unexpected response.",
                    code="evm_invalid_response",
                )
            return payload
        return {}

    async def _get(self, path: str, limit: int) -> list[dict[str, Any]]:
        params: dict[str, str | int | bool] = {"sort": "desc", "limit": limit}
        if path == "erc20-transfers":
            params["excludeZeroValue"] = True
        if self.api_key:
            params["apikey"] = self.api_key
        payload = await self._request_json(f"{self.source_url}/{path}", params)
        items = payload.get("items")
        if not isinstance(items, list):
            raise EvmIndexerError(
                f"{self.display_name} history service returned an unexpected response.",
                code="evm_invalid_response",
            )
        return [item for item in items if isinstance(item, dict)]

    async def get_address_transfers(
        self, address: str, signature_limit: int
    ) -> TransferFetchResult:
        if self.provider == "blockscout":
            return await self._get_blockscout_transfers(address, signature_limit)
        if self.provider == "three_xpl":
            return await self._get_three_xpl_transfers(address, signature_limit)
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

    async def _get_blockscout_transfers(
        self, address: str, signature_limit: int
    ) -> TransferFetchResult:
        prefix = f"addresses/{address.lower()}"
        normal_payload, token_payload = await asyncio.gather(
            self._request_json(f"{self.source_url}/{prefix}/transactions", {}),
            self._request_json(f"{self.source_url}/{prefix}/token-transfers", {}),
        )
        normal_items = _dict_items(normal_payload)[:signature_limit]
        token_items = _dict_items(token_payload)[:signature_limit]
        transfers = [
            *self.normalize_native_transactions(normal_items),
            *self.normalize_token_transfers(token_items),
        ]
        return self._bounded_result(transfers, normal_items, token_items, signature_limit)

    async def _get_three_xpl_transfers(
        self, address: str, signature_limit: int
    ) -> TransferFetchResult:
        params: dict[str, str | int | bool] = {
            "data": "events",
            "from": "all",
            "limit": 10 if signature_limit <= 10 else 100,
            "page": "-0",
            "token": THREE_XPL_PUBLIC_TOKEN,
        }
        payload = await self._request_json(f"{self.source_url}/address/{address.lower()}", params)
        events = payload.get("data", {}).get("events", {})
        transaction_ids: list[str] = []
        if isinstance(events, dict):
            for module_events in events.values():
                if not isinstance(module_events, list):
                    continue
                for event in module_events:
                    transaction = event.get("transaction") if isinstance(event, dict) else None
                    if transaction and transaction not in transaction_ids:
                        transaction_ids.append(str(transaction))
                    if len(transaction_ids) >= signature_limit:
                        break
                if len(transaction_ids) >= signature_limit:
                    break

        async def fetch_transaction(transaction: str) -> dict[str, Any] | None:
            try:
                return await self._request_json(
                    f"{self.source_url}/transaction/{transaction}",
                    {
                        "data": "transaction,events",
                        "from": "all",
                        "limit": 100,
                        "library": "currencies",
                        "token": THREE_XPL_PUBLIC_TOKEN,
                    },
                )
            except EvmIndexerError:
                return None

        details = await asyncio.gather(
            *(fetch_transaction(transaction) for transaction in transaction_ids)
        )
        successful = [detail for detail in details if detail is not None]
        transfers = [
            transfer
            for detail in successful
            for transfer in self.normalize_three_xpl_transaction(detail)
        ]
        transfers.sort(
            key=lambda item: item.timestamp.timestamp() if item.timestamp else 0,
            reverse=True,
        )
        return TransferFetchResult(
            transfers=transfers,
            signatures_seen=len(transaction_ids),
            transactions_processed=len(successful),
            transactions_failed=len(transaction_ids) - len(successful),
        )

    def _bounded_result(
        self,
        transfers: list[Transfer],
        normal_items: list[dict[str, Any]],
        token_items: list[dict[str, Any]],
        signature_limit: int,
    ) -> TransferFetchResult:
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
            str(
                item.get("id")
                or item.get("txHash")
                or item.get("hash")
                or item.get("transaction_hash")
            )
            for item in [*normal_items, *token_items]
            if item.get("id")
            or item.get("txHash")
            or item.get("hash")
            or item.get("transaction_hash")
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
            source = _address(item.get("from"))
            target = _address(item.get("to"))
            signature = item.get("id") or item.get("txHash") or item.get("hash")
            raw_value = item.get("value")
            if not source or not target or not signature or raw_value is None:
                continue
            status = item.get("status")
            if status in {False, "error", "failed"}:
                continue
            amount = Decimal(str(raw_value)) / Decimal(10**18)
            if amount <= 0:
                continue
            transfers.append(
                Transfer(
                    id=f"evm:{self.chain_id}:{signature}:native",
                    signature=str(signature),
                    slot=int(item.get("blockNumber") or item.get("block_number") or 0),
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
            source = _address(item.get("from"))
            target = _address(item.get("to"))
            signature = item.get("txHash") or item.get("id") or item.get("transaction_hash")
            total = item.get("total") if isinstance(item.get("total"), dict) else {}
            token = item.get("token") if isinstance(item.get("token"), dict) else {}
            raw_amount = (
                item.get("amount") if item.get("amount") is not None else total.get("value")
            )
            if not source or not target or not signature or raw_amount is None:
                continue
            decimals = int(
                item.get("tokenDecimals") or total.get("decimals") or token.get("decimals") or 0
            )
            amount = Decimal(str(raw_amount)) / (Decimal(10) ** decimals)
            if amount <= 0:
                continue
            token_address = str(
                item.get("tokenAddress") or token.get("address_hash") or "ERC20"
            ).lower()
            symbol = str(item.get("tokenSymbol") or token.get("symbol") or "").strip()
            asset = symbol if re.fullmatch(r"[A-Za-z0-9._-]{1,18}", symbol) else token_address
            log_index = item.get("logIndex", item.get("log_index", 0))
            transfers.append(
                Transfer(
                    id=f"evm:{self.chain_id}:{signature}:log:{log_index}",
                    signature=str(signature),
                    slot=int(item.get("blockNumber") or item.get("block_number") or 0),
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

    def normalize_three_xpl_transaction(self, payload: dict[str, Any]) -> list[Transfer]:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        transaction = data.get("transaction") if isinstance(data.get("transaction"), dict) else {}
        signature = str(transaction.get("transaction") or "")
        if not signature:
            return []
        block = int(transaction.get("block") or 0)
        timestamp = _timestamp(transaction.get("time"))
        modules = data.get("events") if isinstance(data.get("events"), dict) else {}
        currencies = payload.get("library", {}).get("currencies", {})
        transfers: list[Transfer] = []
        for module, raw_events in modules.items():
            if not isinstance(raw_events, list):
                continue
            events = [
                item
                for item in raw_events
                if isinstance(item, dict) and not item.get("failed") and item.get("extra") != "f"
            ]
            used_positive: set[int] = set()
            for source_event in events:
                source_effect = Decimal(str(source_event.get("effect") or "0"))
                if source_effect >= 0:
                    continue
                currency = str(source_event.get("currency") or "bnb")
                target_index = next(
                    (
                        index
                        for index, target_event in enumerate(events)
                        if index not in used_positive
                        and str(target_event.get("currency") or "bnb") == currency
                        and Decimal(str(target_event.get("effect") or "0")) == -source_effect
                    ),
                    None,
                )
                if target_index is None:
                    continue
                used_positive.add(target_index)
                target_event = events[target_index]
                source = str(source_event.get("address") or "").lower()
                target = str(target_event.get("address") or "").lower()
                if not source or not target or source == target:
                    continue
                metadata = currencies.get(currency, {}) if isinstance(currencies, dict) else {}
                decimals = int(metadata.get("decimals") or 18)
                amount = -source_effect / (Decimal(10) ** decimals)
                symbol = str(metadata.get("symbol") or self.native_asset).strip()
                asset = symbol if re.fullmatch(r"[A-Za-z0-9._-]{1,18}", symbol) else currency
                source_sort = source_event.get("sort_key", 0)
                target_sort = target_event.get("sort_key", 0)
                transfers.append(
                    Transfer(
                        id=f"3xpl:{self.chain_id}:{signature}:{module}:{source_sort}:{target_sort}",
                        signature=signature,
                        slot=block,
                        timestamp=timestamp,
                        source=source,
                        target=target,
                        asset=asset,
                        amount=format(amount, "f"),
                        decimals=decimals,
                        kind="native_transfer" if currency == "bnb" else "token_transfer",
                        instruction_path=f"3xpl:{module}:{source_sort}:{target_sort}",
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


def _address(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("hash") or value.get("address_hash")
    return str(value) if value else None


def _dict_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
