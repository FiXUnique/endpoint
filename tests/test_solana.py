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
