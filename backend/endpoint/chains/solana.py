from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from endpoint.models import Transfer


class SolanaRpcError(RuntimeError):
    """Raised when a Solana RPC request fails or returns an invalid result."""


class SolanaAdapter:
    chain = "solana"

    def __init__(self, rpc_url: str, timeout: float = 20) -> None:
        self.rpc_url = rpc_url
        self._client = httpx.AsyncClient(timeout=timeout)
        self._request_id = 0

    async def close(self) -> None:
        await self._client.aclose()

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        try:
            response = await self._client.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": method,
                    "params": params,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SolanaRpcError(f"Solana RPC request failed: {exc}") from exc
        if payload.get("error"):
            message = payload["error"].get("message", "unknown RPC error")
            raise SolanaRpcError(f"Solana RPC error: {message}")
        return payload.get("result")

    async def get_address_transfers(
        self, address: str, signature_limit: int
    ) -> tuple[list[Transfer], int]:
        signatures = await self._rpc(
            "getSignaturesForAddress",
            [address, {"limit": signature_limit, "commitment": "confirmed"}],
        )
        if not isinstance(signatures, list):
            raise SolanaRpcError("getSignaturesForAddress returned a non-list result")

        semaphore = asyncio.Semaphore(8)

        async def fetch(signature: str) -> dict[str, Any] | None:
            async with semaphore:
                return await self._rpc(
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

        transactions = await asyncio.gather(
            *(fetch(item["signature"]) for item in signatures if not item.get("err"))
        )
        transfers: list[Transfer] = []
        valid_signatures = [item for item in signatures if not item.get("err")]
        for signature_info, transaction in zip(valid_signatures, transactions, strict=True):
            if transaction:
                transfers.extend(
                    self.normalize_transaction(signature_info["signature"], transaction)
                )
        return transfers, len(signatures)

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
