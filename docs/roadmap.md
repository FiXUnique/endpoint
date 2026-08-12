# Phased roadmap

## Phase 0 — delivered vertical slice

Live Solana wallet RPC, normalized parsed transfers, graph exploration, recursive bounded expansion,
fact/heuristic separation, reproducible scoring, snapshots, evidence export, tests, and synthetic demo.

## Phase 1 — trustworthy Solana depth

- pagination and configurable trace budgets
- balance-delta reconciliation for unsupported parsed instructions
- Token-2022 support
- mint/deployer and token-account discovery
- versioned Jupiter/Raydium/Orca/Pump.fun parsers
- launch-window and funding-tree bundle signals
- transaction caching and raw response hashing

Exit criterion: a mint seed reconstructs creation through post-launch flows from real evidence.

## Phase 2 — case workflow

Case search, investigator notes/manual labels, provenance catalogue, timelines, graph filters,
common-ancestor/destination paths, CSV/PDF reports, and portable evidence archives.

## Phase 3 — historical intelligence

PostgreSQL schema, worker queue, incremental indexing, repeated-infrastructure search, campaign graphs,
evaluation datasets, heuristic calibration, and alert-safe risk indicators.

## Phase 4 — chain and bridge expansion

EVM adapter, bridge protocol parsers, candidate destination correlation, observable privacy-system
boundaries, and live investigation subscriptions. Every correlation retains uncertainty and competing
candidates.
