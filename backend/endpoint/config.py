from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    solana_rpc_url: str = os.getenv(
        "SOLANA_RPC_URL", "https://api.mainnet.solana.com"
    )
    rpc_timeout_seconds: float = float(os.getenv("SOLANA_RPC_TIMEOUT_SECONDS", "20"))
    rpc_max_retries: int = min(int(os.getenv("SOLANA_RPC_MAX_RETRIES", "3")), 6)
    rpc_min_interval_seconds: float = max(
        float(os.getenv("SOLANA_RPC_MIN_INTERVAL_SECONDS", "0.28")), 0
    )
    rpc_concurrency: int = min(max(int(os.getenv("SOLANA_RPC_CONCURRENCY", "3")), 1), 8)
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
