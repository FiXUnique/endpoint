import httpx
import pytest
from endpoint.chains.evm import EvmAdapter
from endpoint.models import TraceRequest
from pydantic import ValidationError

ADDRESS = "0xec149f3cdb488e4001fba55b9114f89139fd3577"


def test_trace_request_accepts_evm_and_still_rejects_wrong_format():
    request = TraceRequest(chain="ethereum", address=ADDRESS)
    assert request.address == ADDRESS

    with pytest.raises(ValidationError, match="EVM addresses must start with 0x"):
        TraceRequest(chain="ethereum", address="Seed111111111111111111111111111111111111")


def test_normalizes_native_and_erc20_transfers():
    adapter = EvmAdapter("ethereum")
    native = adapter.normalize_native_transactions(
        [
            {
                "id": "0xabc",
                "chainId": "1",
                "timestamp": "2026-08-13T12:00:00.000Z",
                "blockNumber": 42,
                "from": ADDRESS.upper().replace("0X", "0x"),
                "to": "0x1111111111111111111111111111111111111111",
                "value": "1250000000000000000",
                "status": True,
            }
        ]
    )
    tokens = adapter.normalize_token_transfers(
        [
            {
                "chainId": "1",
                "blockNumber": 43,
                "txHash": "0xdef",
                "logIndex": 7,
                "from": "0x1111111111111111111111111111111111111111",
                "to": ADDRESS,
                "amount": "1234500",
                "tokenAddress": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "tokenSymbol": "USDC",
                "tokenDecimals": 6,
                "timestamp": "2026-08-13T12:01:00.000Z",
            }
        ]
    )

    assert native[0].amount == "1.25"
    assert native[0].asset == "ETH"
    assert native[0].source == ADDRESS
    assert tokens[0].amount == "1.2345"
    assert tokens[0].asset == "USDC"
    assert tokens[0].instruction_path.endswith("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")


def test_deceptive_token_symbol_falls_back_to_contract_address():
    adapter = EvmAdapter("ethereum")
    transfers = adapter.normalize_token_transfers(
        [
            {
                "blockNumber": 1,
                "txHash": "0xabc",
                "logIndex": 1,
                "from": ADDRESS,
                "to": "0x1111111111111111111111111111111111111111",
                "amount": "1",
                "tokenAddress": "0x2222222222222222222222222222222222222222",
                "tokenSymbol": "EṬH",
                "tokenDecimals": 0,
            }
        ]
    )

    assert transfers[0].asset == "0x2222222222222222222222222222222222222222"


@pytest.mark.asyncio
async def test_fetches_keyless_history_and_combines_transaction_types():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/transactions"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "0xabc",
                            "timestamp": "2026-08-13T12:00:00.000Z",
                            "blockNumber": 42,
                            "from": ADDRESS,
                            "to": "0x1111111111111111111111111111111111111111",
                            "value": "1000000000000000000",
                            "status": True,
                        }
                    ],
                    "link": {},
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "chainId": "1",
                        "blockNumber": 43,
                        "txHash": "0xdef",
                        "logIndex": 2,
                        "from": ADDRESS,
                        "to": "0x2222222222222222222222222222222222222222",
                        "amount": "2500000",
                        "tokenAddress": "0xtoken",
                        "tokenSymbol": "USDC",
                        "tokenDecimals": 6,
                        "timestamp": "2026-08-13T12:01:00.000Z",
                    }
                ],
                "link": {},
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = EvmAdapter("ethereum", client=client)
        result = await adapter.get_address_transfers(ADDRESS, 10)

    assert len(result.transfers) == 2
    assert result.signatures_seen == 2
    assert {transfer.asset for transfer in result.transfers} == {"ETH", "USDC"}


@pytest.mark.asyncio
async def test_empty_evm_address_is_a_valid_empty_result():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "link": {}}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = EvmAdapter("ethereum", client=client)
        result = await adapter.get_address_transfers(ADDRESS, 25)

    assert result.transfers == []
    assert result.signatures_seen == 0
