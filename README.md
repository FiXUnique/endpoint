# Endpoint

**Evidence-first, open-source on-chain investigations.**

Endpoint is an investigator-oriented platform for answering a difficult question from public
blockchain data: **where did the money ultimately go?** The first vertical slice traces a Solana
wallet's recent transaction history, normalizes native and SPL-token transfers, builds an
interactive fund-flow graph, supports recursive wallet expansion, preserves transaction evidence,
and separates confirmed facts from scored heuristics.

> [!IMPORTANT]
> Endpoint does not identify people, determine guilt, or treat correlation as ownership. An
> evidence score measures the strength of configured observable signals. It is not a probability
> that two addresses share an owner.

## What works today

- Live Solana mainnet JSON-RPC ingestion (`getSignaturesForAddress` + parsed transactions)
- Normalized SOL and SPL-token transfers, including inner instructions where RPC parsing exists
- Interactive Cytoscape fund-flow graph with fact/heuristic visual separation
- Click-through evidence inspection for every edge
- Recursive expansion of any observed wallet
- Deterministic common-funder and temporal-proximity heuristics
- Candidate consolidation ranking based on observed multi-source convergence
- Explicit RPC-limit/truncation notices
- Durable SQLite investigation snapshots and JSON evidence export
- Clearly labelled, reproducible synthetic demonstration
- Chain-neutral adapter and persistence boundaries for future extension

The current slice accepts **wallet addresses**. Token-mint launch reconstruction, protocol
decoders, bundle detection, historical campaigns, cross-chain bridges, PDF reports, and live
monitoring are roadmap work—not hidden or simulated features.

## Quick start

Requirements: Python 3.11+, Node.js 20+.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env            # Windows: copy .env.example .env
uvicorn endpoint.main:app --reload
```

In another terminal:

```bash
corepack enable
pnpm install
pnpm run dev
```

Open `http://localhost:5173`. The API documentation is available at
`http://localhost:8000/docs`.

For sustained investigations, set `SOLANA_RPC_URL` to an RPC service you operate or are authorized
to use. Public endpoints are rate-limited.

### Docker Compose

```bash
docker compose up --build
```

## A complete workflow

1. Paste a Solana wallet address and choose a transaction limit.
2. Endpoint retrieves real transactions from the configured RPC.
3. Parsed SOL/SPL transfer instructions become immutable evidence records.
4. Confirmed transfers render as solid directed edges.
5. Reproducible relationships render as dashed edges with their component signals.
6. Select any edge to inspect transaction signatures, slots, times, values, and explanations.
7. Select a wallet and expand it to merge another bounded transaction slice.
8. Export the saved evidence snapshot as JSON.

The “Open synthetic demo” action demonstrates split and consolidation behavior without making
network calls. Its fake addresses and signatures are visibly labelled and never enter production
analysis paths.

## Architecture

```text
React / Cytoscape UI
        │ JSON/HTTP
        ▼
FastAPI investigation service
        ├── ChainAdapter (chain-neutral)
        │      └── SolanaAdapter (RPC + instruction normalization)
        ├── deterministic graph / confidence analysis
        └── snapshot repository (SQLite MVP; replaceable boundary)
```

The MVP intentionally remains a modular monolith. PostgreSQL, Redis, and background workers become
useful when multi-user ingestion and longer traces arrive; requiring them now would make local use
harder without improving this bounded workflow.

- `backend/endpoint/chains/base.py`: adapter contract that analysis depends on
- `backend/endpoint/chains/solana.py`: all Solana RPC and instruction-specific behavior
- `backend/endpoint/analysis.py`: chain-neutral graph/evidence rules
- `backend/endpoint/repository.py`: durable investigation snapshot boundary
- `src/components/GraphCanvas.tsx`: graph rendering and interaction
- `src/components/Inspector.tsx`: evidence and confidence explanations

See [architecture](docs/architecture.md), [methodology](docs/methodology.md), and the
[data model](docs/data-model.md) for the design rationale.

## Confidence and evidence

Endpoint uses four explicit certainty classes:

| Class | Meaning |
| --- | --- |
| `confirmed_fact` | Directly parsed from public chain data |
| `deterministic_relationship` | Necessarily derived from confirmed facts |
| `heuristic_relationship` | Observable signals support a hypothesis |
| `weak_correlation` | Evidence exists but remains low strength |

Current heuristic scores use a versioned additive formula with capped contributions. For example,
a common funder contributes `0.45`; funding within the same 120-second window contributes up to
`0.20`. Every contribution points to evidence IDs. Scores are deterministic and testable, but not
calibrated probabilities. See [methodology](docs/methodology.md).

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health and configuration status |
| `POST /api/v1/investigations/trace` | Create and save a bounded live wallet trace |
| `POST /api/v1/investigations/expand` | Expand a wallet in an existing live investigation |
| `GET /api/v1/investigations` | List saved cases |
| `GET /api/v1/investigations/{id}` | Retrieve a saved evidence snapshot |
| `GET /api/v1/investigations/{id}/export` | Download JSON evidence |
| `GET /api/v1/demo` | Load the transparent synthetic fixture |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/investigations/trace \
  -H "Content-Type: application/json" \
  -d '{"address":"YOUR_SOLANA_ADDRESS","signature_limit":25}'
```

## Limitations

- Parsed transfers depend on the configured RPC's `jsonParsed` response. Unsupported or opaque
  program instructions are preserved only by the upstream transaction, not falsely decoded.
- The current trace is signature-count bounded and one address expansion at a time. Reaching a
  limit is visibly reported.
- Token-account ownership is inferred only from transaction token-balance metadata when present.
- Consolidation candidates are convergence hypotheses, not verified exchanges, exit points, or
  identity attribution.
- Common funding can describe normal user or service behavior. It is evidence to inspect, not proof.
- SQLite snapshots optimize local reproducibility, not multi-user concurrency or chain indexing.

## Testing

```bash
ruff check .
pytest
pnpm run lint
pnpm test
pnpm run build
```

Fixtures test normalization, deterministic scores, evidence preservation, snapshot round-trips,
and truthful demo labelling. Heuristic tests assert reproducible outputs and known limitations; they
do not label every positive result as “correct ownership.” Future calibration uses labelled public
datasets with train/evaluation separation and precision/recall by signal family.

## Roadmap

1. **Vertical slice (current):** live wallet tracing, normalization, graph, expansion, evidence,
   transparent relationships, snapshots, export.
2. **Solana depth:** mint entry points, Token-2022, balance-delta fallback, DEX/launchpad parsers,
   Pump.fun lifecycle and bounded bundle analysis.
3. **Investigation workflow:** case notes, manual labels with provenance, timelines, filters,
   CSV/PDF reports, deterministic evidence archives.
4. **Historical intelligence:** PostgreSQL ingestion, background jobs, entity catalogue, campaign
   graph, calibrated heuristics and evaluation datasets.
5. **Cross-chain:** EVM adapters, bridge event correlation with uncertainty boundaries, optional
   live monitoring.

## Open-source strategy and license

Endpoint uses the [Apache License 2.0](LICENSE): permissive commercial use encourages adoption and
integration, while explicit patent terms are valuable for an infrastructure/security project. The
tradeoff is that commercial derivatives need not publish their modifications. A copyleft license
would maximize code-sharing obligations but can reduce integration by exchanges and analytics
teams. The open core here is deliberately useful; scale, private data, enterprise authentication,
and proprietary attribution can remain separate without degrading public functionality.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
