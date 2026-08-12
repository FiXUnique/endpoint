from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from endpoint import __version__
from endpoint.chains.solana import SolanaAdapter, SolanaRpcError
from endpoint.config import settings
from endpoint.models import ExpandRequest, HealthResponse, InvestigationGraph, TraceRequest
from endpoint.repository import InvestigationRepository
from endpoint.service import InvestigationService

adapter = SolanaAdapter(settings.solana_rpc_url, settings.rpc_timeout_seconds)
repository = InvestigationRepository(settings.database_path)
service = InvestigationService(adapter, repository, settings.solana_rpc_url)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await adapter.close()


app = FastAPI(
    title="Endpoint Forensics API",
    version=__version__,
    description="Evidence-first Solana fund-flow investigation API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(SolanaRpcError)
async def rpc_error_handler(_, exc: SolanaRpcError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def get_service() -> InvestigationService:
    return service


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__, rpc_configured=bool(settings.solana_rpc_url))


@app.post("/api/v1/investigations/trace", response_model=InvestigationGraph)
async def trace_investigation(
    request: TraceRequest,
    investigation_service: Annotated[InvestigationService, Depends(get_service)],
) -> InvestigationGraph:
    return await investigation_service.trace(
        request.address, request.signature_limit, request.name
    )


@app.get("/api/v1/investigations", response_model=list[dict[str, str]])
async def list_investigations(limit: Annotated[int, Query(ge=1, le=100)] = 25):
    return repository.list(limit)


@app.post("/api/v1/investigations/expand", response_model=InvestigationGraph)
async def expand_investigation(
    request: ExpandRequest,
    investigation_service: Annotated[InvestigationService, Depends(get_service)],
) -> InvestigationGraph:
    try:
        graph = await investigation_service.expand(
            request.investigation_id, request.address, request.signature_limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if graph is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return graph


@app.get("/api/v1/investigations/{investigation_id}", response_model=InvestigationGraph)
async def get_investigation(investigation_id: str) -> InvestigationGraph:
    graph = repository.get(investigation_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return graph


@app.get("/api/v1/investigations/{investigation_id}/export")
async def export_investigation(investigation_id: str) -> JSONResponse:
    graph = repository.get(investigation_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return JSONResponse(
        content=graph.model_dump(mode="json"),
        headers={
            "Content-Disposition": f'attachment; filename="{investigation_id}.json"',
            "X-Endpoint-Methodology-Version": graph.methodology_version,
        },
    )


@app.get("/api/v1/demo", response_model=InvestigationGraph)
async def synthetic_demo(
    investigation_service: Annotated[InvestigationService, Depends(get_service)],
) -> InvestigationGraph:
    return investigation_service.demo()


def _web_distribution() -> Path | None:
    """Find the built UI in a checkout or a PyInstaller bundle."""
    candidates = []
    if configured := os.getenv("ENDPOINT_WEB_DIST"):
        candidates.append(Path(configured))
    if bundle_root := getattr(sys, "_MEIPASS", None):
        candidates.append(Path(bundle_root) / "web")
    candidates.append(Path(__file__).resolve().parents[2] / "dist")
    return next((path for path in candidates if (path / "index.html").is_file()), None)


if web_distribution := _web_distribution():
    # Mounted last so API and OpenAPI routes retain priority.
    app.mount("/", StaticFiles(directory=web_distribution, html=True), name="web")
