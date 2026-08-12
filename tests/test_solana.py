import httpx
import pytest
from endpoint.chains.solana import SolanaAdapter


def test_normalizes_native_and_spl_transfers():
    transaction = {
        "slot": 42,
        "blockTime": 1_700_000_000,
        "transaction": {
            "message": {
                "accountKeys": [
                    {"pubkey": "WalletSource"},
                    {"pubkey": "WalletTarget"},
                    {"pubkey": "TokenAccountSource"},
                    {"pubkey": "TokenAccountTarget"},
                ],
                "instructions": [
                    {
                        "parsed": {
                            "type": "transfer",
                            "info": {
                                "source": "WalletSource",
                                "destination": "WalletTarget",
                                "lamports": 1_250_000_000,
                            },
                        }
                    },
                    {
                        "parsed": {
                            "type": "transferChecked",
                            "info": {
                                "source": "TokenAccountSource",
                                "destination": "TokenAccountTarget",
                                "mint": "TokenMint",
                                "tokenAmount": {"amount": "12345", "decimals": 2},
                            },
                        }
                    },
                ],
            }
        },
        "meta": {
            "preTokenBalances": [
                {
                    "accountIndex": 2,
                    "mint": "TokenMint",
                    "owner": "WalletSource",
                    "uiTokenAmount": {"decimals": 2},
                },
                {
                    "accountIndex": 3,
                    "mint": "TokenMint",
                    "owner": "WalletTarget",
                    "uiTokenAmount": {"decimals": 2},
                },
            ]
        },
    }

    transfers = SolanaAdapter.normalize_transaction("Signature", transaction)

    assert len(transfers) == 2
    assert transfers[0].amount == "1.25"
    assert transfers[0].asset == "SOL"
    assert transfers[1].amount == "123.45"
    assert transfers[1].source == "WalletSource"
    assert transfers[1].target == "WalletTarget"
    assert transfers[1].asset == "TokenMint"


def test_ignores_unparsed_and_zero_value_instructions():
    transaction = {
        "slot": 1,
        "transaction": {
            "message": {
                "accountKeys": [],
                "instructions": [
                    {"data": "opaque"},
                    {
                        "parsed": {
                            "type": "transfer",
                            "info": {"source": "A", "destination": "B", "lamports": 0},
                        }
                    },
                ],
            }
        },
        "meta": {},
    }
    assert SolanaAdapter.normalize_transaction("Signature", transaction) == []


@pytest.mark.asyncio
async def test_retries_http_429_and_honors_bounded_retry_path():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": []},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = SolanaAdapter(
            "https://api.mainnet.solana.com",
            max_retries=1,
            min_request_interval=0,
            client=client,
        )
        result = await adapter._rpc("getSignaturesForAddress", ["address"])

    assert result == []
    assert calls == 2


@pytest.mark.asyncio
async def test_keeps_successful_transactions_when_one_rpc_item_fails(monkeypatch):
    adapter = SolanaAdapter(
        "https://api.mainnet.solana.com",
        max_retries=0,
        min_request_interval=0,
    )
    transaction = {
        "slot": 42,
        "transaction": {
            "message": {
                "accountKeys": [],
                "instructions": [
                    {
                        "parsed": {
                            "type": "transfer",
                            "info": {
                                "source": "WalletSource",
                                "destination": "WalletTarget",
                                "lamports": 1_000_000_000,
                            },
                        }
                    }
                ],
            }
        },
        "meta": {},
    }

    async def rpc(method, params):
        if method == "getSignaturesForAddress":
            return [{"signature": "good"}, {"signature": "limited"}]
        if params[0] == "good":
            return transaction
        from endpoint.chains.solana import SolanaRpcError

        raise SolanaRpcError(
            "rate limited", code="rpc_rate_limited", retryable=True
        )

    monkeypatch.setattr(adapter, "_rpc", rpc)
    try:
        result = await adapter.get_address_transfers("WalletSource", 2)
    finally:
        await adapter.close()

    assert len(result.transfers) == 1
    assert result.signatures_seen == 2
    assert result.transactions_processed == 1
    assert result.transactions_failed == 1
