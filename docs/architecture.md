# Architecture and MVP

## Repository assessment

The repository began empty, with no commits or reusable implementation. Endpoint therefore starts
with explicit boundaries rather than migration constraints.

## Realistic MVP

The implemented workflow accepts a Solana or supported EVM wallet, retrieves a bounded public
history slice, normalizes supported transfers, preserves evidence, calculates relationships
deterministically, saves the graph, and lets an investigator inspect and expand it.

A token-mint investigation is materially different: it requires mint/deployer resolution, protocol
decoders, launch windows, holder snapshots, and balance-delta analysis. It belongs in the next phase
instead of being superficially routed through the wallet tracer.

## Components

### Chain-agnostic

- normalized transfers and evidence references
- investigation lifecycle and limits
- graph construction and aggregation
- confidence signals and relationship classes
- consolidation/convergence ranking
- snapshot persistence and export
- graph interaction and evidence inspector

### Solana-specific

- JSON-RPC methods and pagination semantics
- base58 address validation
- `jsonParsed` System/SPL Token instruction handling
- inner instruction traversal
- token account owner/mint resolution from token balances
- future Token-2022, Pump.fun, DEX and launchpad parsers

### EVM-specific

- explicit network selection for identical `0x` address formats
- keyless Routescan indexed-history retrieval
- native-value and ERC-20 transfer normalization
- chain-specific native symbols and explorer links
- Ethereum, Base, BNB Smart Chain, Polygon, Arbitrum, Optimism, Avalanche, and Robinhood Chain adapters

## Why this stack

- **FastAPI/Python:** typed contracts and a natural path to NetworkX/scientific evaluation without
  requiring it for the small current algorithms.
- **React/Vite:** a small client build independent of API deployment.
- **Cytoscape.js:** mature interactive graph styling/selection, compound-node potential, and larger
  graph support than a DOM-based flow editor.
- **SQLite now:** zero-service local persistence behind a replaceable interface. PostgreSQL becomes
  appropriate with concurrent users, normalized indexing, and historical search.
- **Modular monolith:** debuggable and locally runnable. Background jobs/Redis are deferred until a
  trace can outlive an HTTP request.

## Hardest technical problems

1. **Complete economic interpretation.** Parsed instructions miss custom program semantics; account
   balance deltas can be ambiguous around swaps and rent. Protocol-specific parsers require versioned
   fixtures and careful reconciliation.
2. **Graph explosion.** Active service wallets and dust create huge fan-out. Expansion must carry
   explicit budgets for depth, time, value, degree, and RPC calls, plus collapsed service entities.
3. **Attribution calibration.** Common-funder and timing signals are correlated and base rates vary.
   Scores must be evaluated against known-positive and hard-negative datasets, not guessed into
   “probabilities.”
4. **Historical/cross-chain state.** Finding campaigns requires indexed history; bridge correlation
   requires chain finality, amount/fee models, time windows, and explicit uncertainty gaps.
5. **Evidence reproducibility.** Providers can differ and metadata can change. Durable reports should
   hash raw response snapshots and record parser/methodology versions.

## Scaling path and safeguards

The synchronous slice caps signatures and eight concurrent transaction requests. Every cap is
returned to the client. Next safeguards are per-investigation RPC budgets, address-degree ceilings,
minimum value/time filters, dust/spam classification, known-service collapsing, task queues, cached
transaction blobs keyed by signature, and incremental graph summaries.

Expected bottlenecks are per-signature RPC calls, repeated decoding across investigations, SQLite
write serialization, O(n²) recipient pairing for high-degree funders, and graph-layout complexity.
Before scale, pair generation must skip/collapse high-degree known services and analysis must run
incrementally over indexed transfers.
