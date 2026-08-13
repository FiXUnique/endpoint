from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

import httpx

from endpoint.chains.base import TransferFetchResult
from endpoint.models import Transfer

logger = logging.getLogger(__name__)


class SolanaRpcError(RuntimeError):
    """Raised when a Solana RPC request fails or returns an invalid result."""

    def __init__(
        self, message: str, *, code: str = "rpc_error", retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SolanaAdapter:
    chain = "solana"
    display_name = "Solana"
    native_asset = "SOL"

    def __init__(
        self,
        rpc_url: str,
        timeout: float = 20,
        *,
        max_retries: int = 3,
        min_request_interval: float = 0.28,
        concurrency: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.rpc_url = rpc_url
        self.source_url = rpc_url
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None
        self._request_id = 0
        self._max_retries = max(max_retries, 0)
        self._min_request_interval = max(min_request_interval, 0)
        self._concurrency = max(concurrency, 1)
        self._request_gate = asyncio.Lock()
        self._last_request_at = 0.0

    @property
    def provider_name(self) -> str:
        parsed = urlsplit(self.rpc_url)
        return parsed.hostname or "configured provider"

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _pace_request(self) -> None:
        async with self._request_gate:
            loop = asyncio.get_running_loop()
            remaining = self._min_request_interval - (loop.time() - self._last_request_at)
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request_at = loop.time()

    @staticmethod
    def _retry_after(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(max(float(value), 0.1), 8.0)
            except ValueError:
                pass
        return min(0.75 * (2**attempt), 8.0)

    @staticmethod
    def _payload_is_rate_limited(payload: dict[str, Any]) -> bool:
        error = payload.get("error") or {}
        message = str(error.get("message", "")).lower()
        return error.get("code") == 429 or "rate limit" in message

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        request_id = self._request_id
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        for attempt in range(self._max_retries + 1):
            await self._pace_request()
            try:
                response = await self._client.post(self.rpc_url, json=request)
            except httpx.HTTPError as exc:
                if attempt < self._max_retries:
                    delay = min(0.75 * (2**attempt), 8.0)
                    logger.warning(
                        "Solana RPC transport error; retrying",
                        extra={"method": method, "attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                    continue
                raise SolanaRpcError(
                    f"Solana RPC transport failed at {self.provider_name} after "
                    f"{attempt + 1} attempts: {type(exc).__name__}",
                    code="rpc_transport_error",
                    retryable=True,
                ) from exc

            if response.status_code == 429:
                delay = self._retry_after(response, attempt)
                if attempt < self._max_retries:
                    logger.warning(
                        "Solana RPC rate limited; retrying",
                        extra={"method": method, "attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)
                    continue
                raise SolanaRpcError(
                    f"Solana RPC at {self.provider_name} remained rate-limited after "
                    f"{attempt + 1} attempts. Try 10 transactions, wait a minute, or start "
                    "Endpoint with --rpc-url pointing to a dedicated Solana provider.",
                    code="rpc_rate_limited",
                    retryable=True,
                )

            try:
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                retryable = response.status_code >= 500
                if retryable and attempt < self._max_retries:
                    await asyncio.sleep(min(0.75 * (2**attempt), 8.0))
                    continue
                raise SolanaRpcError(
                    f"Solana RPC at {self.provider_name} returned an invalid response "
                    f"({response.status_code}).",
                    code="rpc_invalid_response",
                    retryable=retryable,
                ) from exc

            if not isinstance(payload, dict):
                raise SolanaRpcError(
                    "Solana RPC returned a non-object response.",
                    code="rpc_invalid_response",
                )
            if self._payload_is_rate_limited(payload):
                if attempt < self._max_retries:
                    await asyncio.sleep(min(0.75 * (2**attempt), 8.0))
                    continue
                raise SolanaRpcError(
                    f"Solana RPC at {self.provider_name} remained rate-limited after retries.",
                    code="rpc_rate_limited",
                    retryable=True,
                )
            if payload.get("error"):
                message = payload["error"].get("message", "unknown RPC error")
                raise SolanaRpcError(
                    f"Solana RPC error from {self.provider_name}: {message}",
                    code="rpc_method_error",
                )
            return payload.get("result")

        raise AssertionError("RPC retry loop exited unexpectedly")

    async def get_address_transfers(
        self, address: str, signature_limit: int
    ) -> TransferFetchResult:
        signatures = await self._rpc(
            "getSignaturesForAddress",
            [address, {"limit": signature_limit, "commitment": "confirmed"}],
        )
        if not isinstance(signatures, list):
            raise SolanaRpcError("getSignaturesForAddress returned a non-list result")

        semaphore = asyncio.Semaphore(self._concurrency)

        async def fetch(
            signature: str,
        ) -> tuple[dict[str, Any] | None, SolanaRpcError | None]:
            async with semaphore:
                try:
                    transaction = await self._rpc(
                        "getTransaction",
                        [
                            signature,
                            {
                                "encoding": "jsonParsed",
                                "commitment": "confirmed",
                                "maxSupportedTransactionVersion": 0,
                            },
                        ],
                    )
                    return transaction, None
                except SolanaRpcError as exc:
                    logger.warning(
                        "Solana transaction unavailable after retries",
                        extra={"signature": signature, "code": exc.code},
                    )
                    return None, exc

        valid_signatures = [
            item
            for item in signatures
            if isinstance(item, dict)
            and not item.get("err")
            and isinstance(item.get("signature"), str)
        ]
        results = await asyncio.gather(
            *(fetch(item["signature"]) for item in valid_signatures)
        )
        transfers: list[Transfer] = []
        failures: list[SolanaRpcError] = []
        unavailable = 0
        processed = 0
        for signature_info, (transaction, failure) in zip(
            valid_signatures, results, strict=True
        ):
            if failure:
                failures.append(failure)
                continue
            if transaction:
                processed += 1
                transfers.extend(
                    self.normalize_transaction(signature_info["signature"], transaction)
                )
            else:
                unavailable += 1
        if valid_signatures and not processed and failures:
            raise failures[-1]
        return TransferFetchResult(
            transfers=transfers,
            signatures_seen=len(signatures),
            transactions_processed=processed,
            transactions_failed=len(failures) + unavailable,
        )

    @staticmethod
    def normalize_transaction(signature: str, transaction: dict[str, Any]) -> list[Transfer]:
        slot = int(transaction.get("slot", 0))
        block_time = transaction.get("blockTime")
        timestamp = datetime.fromtimestamp(block_time, UTC) if block_time else None
        meta = transaction.get("meta") or {}
        message = ((transaction.get("transaction") or {}).get("message") or {})
        account_keys = message.get("accountKeys") or []
        keys = [entry.get("pubkey") if isinstance(entry, dict) else entry for entry in account_keys]
        loaded_addresses = meta.get("loadedAddresses") or {}
        keys.extend(loaded_addresses.get("writable") or [])
        keys.extend(loaded_addresses.get("readonly") or [])

        token_owners: dict[str, str] = {}
        token_decimals: dict[str, int] = {}
        token_balances = [
            *(meta.get("preTokenBalances") or []),
            *(meta.get("postTokenBalances") or []),
        ]
        for balance in token_balances:
            index = balance.get("accountIndex")
            if isinstance(index, int) and index < len(keys):
                account = keys[index]
                if owner := balance.get("owner"):
                    token_owners[account] = owner
                token_decimals[account] = int(
                    (balance.get("uiTokenAmount") or {}).get("decimals", 0)
                )

        groups: list[tuple[str, list[dict[str, Any]]]] = [
            ("outer", message.get("instructions") or [])
        ]
        groups.extend(
            (f"inner:{group.get('index', 0)}", group.get("instructions") or [])
            for group in meta.get("innerInstructions") or []
        )

        transfers: list[Transfer] = []
        for group_name, instructions in groups:
            for index, instruction in enumerate(instructions):
                parsed = instruction.get("parsed") if isinstance(instruction, dict) else None
                if not isinstance(parsed, dict):
                    continue
                info = parsed.get("info") or {}
                instruction_type = parsed.get("type")
                path = f"{group_name}:{index}"
                if instruction_type == "transfer" and "lamports" in info:
                    amount = Decimal(str(info["lamports"])) / Decimal(1_000_000_000)
                    transfer = SolanaAdapter._make_transfer(
                        signature,
                        slot,
                        timestamp,
                        info.get("source"),
                        info.get("destination"),
                        "SOL",
                        amount,
                        9,
                        "native_transfer",
                        path,
                    )
                    if transfer:
                        transfers.append(transfer)
                    continue

                if instruction_type not in {"transfer", "transferChecked"}:
                    continue
                source_account = info.get("source")
                target_account = info.get("destination")
                raw_token_amount = info.get("tokenAmount") or {}
                decimals = int(
                    raw_token_amount.get("decimals", token_decimals.get(source_account, 0))
                )
                raw_amount = raw_token_amount.get("amount", info.get("amount"))
                if raw_amount is None:
                    continue
                amount = Decimal(str(raw_amount)) / (Decimal(10) ** decimals)
                mint = info.get("mint") or SolanaAdapter._mint_for_accounts(
                    source_account, target_account, meta, keys
                )
                transfer = SolanaAdapter._make_transfer(
                    signature,
                    slot,
                    timestamp,
                    token_owners.get(source_account, source_account),
                    token_owners.get(target_account, target_account),
                    mint or "UNKNOWN_SPL_TOKEN",
                    amount,
                    decimals,
                    "token_transfer",
                    path,
                )
                if transfer:
                    transfers.append(transfer)
        return transfers

    @staticmethod
    def _mint_for_accounts(
        source: str | None, target: str | None, meta: dict[str, Any], keys: list[str]
    ) -> str | None:
        token_balances = [
            *(meta.get("preTokenBalances") or []),
            *(meta.get("postTokenBalances") or []),
        ]
        for balance in token_balances:
            index = balance.get("accountIndex")
            if isinstance(index, int) and index < len(keys) and keys[index] in {source, target}:
                return balance.get("mint")
        return None

    @staticmethod
    def _make_transfer(
        signature: str,
        slot: int,
        timestamp: datetime | None,
        source: str | None,
        target: str | None,
        asset: str,
        amount: Decimal,
        decimals: int,
        kind: str,
        path: str,
    ) -> Transfer | None:
        if not source or not target or amount <= 0:
            return None
        identity = f"{signature}:{path}:{source}:{target}:{asset}:{amount}"
        return Transfer(
            id=f"txf_{hashlib.sha256(identity.encode()).hexdigest()[:20]}",
            signature=signature,
            slot=slot,
            timestamp=timestamp,
            source=source,
            target=target,
            asset=asset,
            amount=format(amount, "f"),
            decimals=decimals,
            kind=kind,
            instruction_path=path,
        )
