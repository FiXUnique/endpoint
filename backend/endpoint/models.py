from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Certainty(StrEnum):
    CONFIRMED = "confirmed_fact"
    DETERMINISTIC = "deterministic_relationship"
    HEURISTIC = "heuristic_relationship"
    WEAK = "weak_correlation"


class EvidenceRef(BaseModel):
    id: str
    chain: str = "solana"
    signature: str
    slot: int
    timestamp: datetime | None = None
    source: str
    target: str
    asset: str
    amount: str
    instruction_path: str
    rpc_url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Transfer(BaseModel):
    id: str
    signature: str
    slot: int
    timestamp: datetime | None = None
    source: str
    target: str
    asset: str
    amount: str
    decimals: int = 0
    kind: Literal["native_transfer", "token_transfer"]
    instruction_path: str


class GraphNode(BaseModel):
    id: str
    address: str
    kind: Literal["wallet", "token_account", "program", "unknown"] = "wallet"
    label: str | None = None
    seed: bool = False
    incoming_count: int = 0
    outgoing_count: int = 0
    observed_assets: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    type: str
    contribution: float = Field(ge=0, le=1)
    explanation: str
    evidence_ids: list[str]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    certainty: Certainty
    evidence_score: float = Field(ge=0, le=1)
    label: str
    asset: str | None = None
    amount: str | None = None
    transfer_count: int = 0
    signals: list[Signal] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ExitCandidate(BaseModel):
    address: str
    evidence_score: float = Field(ge=0, le=1)
    label: str
    explanation: str
    contributing_wallets: int
    evidence_ids: list[str]


class TraceLimits(BaseModel):
    requested_signatures: int
    returned_signatures: int
    processed_transactions: int = 0
    failed_transactions: int = 0
    truncated: bool
    notice: str | None = None


class InvestigationGraph(BaseModel):
    investigation_id: str
    name: str
    chain: str = "solana"
    seed: str
    data_source: Literal["live_rpc", "synthetic_demo"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    evidence: list[EvidenceRef]
    exit_candidates: list[ExitCandidate] = Field(default_factory=list)
    limits: TraceLimits
    methodology_version: str = "0.1.0"


class TraceRequest(BaseModel):
    address: str = Field(min_length=32, max_length=44)
    signature_limit: int = Field(default=25, ge=1, le=100)
    name: str | None = Field(default=None, max_length=120)

    @field_validator("address")
    @classmethod
    def address_is_base58(cls, value: str) -> str:
        alphabet = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
        if any(character not in alphabet for character in value):
            raise ValueError("address must be base58 encoded")
        return value


class ExpandRequest(BaseModel):
    investigation_id: str
    address: str = Field(min_length=32, max_length=44)
    signature_limit: int = Field(default=15, ge=1, le=50)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    rpc_configured: bool


class RpcResponse(BaseModel):
    result: Any | None = None
    error: dict[str, Any] | None = None
