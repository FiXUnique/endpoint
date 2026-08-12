from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    solana_rpc_url: str = os.getenv(
        "SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"
    )
    rpc_timeout_seconds: float = float(os.getenv("SOLANA_RPC_TIMEOUT_SECONDS", "20"))
    max_signatures: int = min(int(os.getenv("SOLANA_MAX_SIGNATURES", "50")), 250)
    database_path: str = os.getenv("DATABASE_PATH", ".data/endpoint.db")
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )


settings = Settings()
