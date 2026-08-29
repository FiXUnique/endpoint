# Endpoint

**Open-source Solana and EVM fund-flow investigation with evidence you can inspect.**

Endpoint helps anyone follow public blockchain transfers from a starting wallet and answer:

> Where did the money go, and which wallet is the last stop Endpoint can see?

Choose a network and paste a wallet address. Endpoint supports Solana, Ethereum, Base, BNB Smart
Chain, Polygon, Arbitrum, Optimism, Avalanche, and Robinhood Chain. It retrieves recent public
mainnet transactions, follows supported transfers, and puts one plain-English answer above the map:
**the wallet where the scanned money trail appears to stop**. The starting wallet and stopping
wallet are labelled directly, tiny spam transfers stay out of the way, and every claim links back to
a public blockchain record.

Endpoint does **not** identify people, prove wallet ownership, decide that a crime occurred, or claim
that an observed endpoint is an exchange, off-ramp, or final destination.

## Download the app

The easiest way to use Endpoint is the packaged release. It does not require Python, Node.js, Docker,
PostgreSQL, or a browser extension.

[**Download Endpoint from GitHub Releases**](https://github.com/FiXUnique/endpoint/releases/latest)

### Windows

1. Download `endpoint-windows-x64.zip`.
2. Extract it.
3. Double-click `endpoint.exe`.
4. Endpoint opens in your browser at `http://127.0.0.1:8765`.

If an older Endpoint process is still using port 8765, the new version automatically chooses the
next available local port and opens that address so the browser cannot silently remain on the old
build.

Endpoint does not cache its local interface between packaged versions. If the graph renderer fails,
the application keeps the investigation visible and provides an explicit reload action.

Windows SmartScreen may warn that the application is unrecognized because the open-source binary is
not code-signed yet. Only run a binary downloaded from this repository's official Releases page.

### Linux

1. Download and extract `endpoint-linux-x64.tar.gz`.
2. Run `./endpoint`.
3. Open `http://127.0.0.1:8765` if a browser does not open automatically.

Your saved investigations remain on your computer:

- Windows: `%LOCALAPPDATA%\Endpoint\endpoint.db`
- Linux: `~/.local/share/endpoint/endpoint.db`

Use another Solana RPC provider when the public endpoint rate-limits you:

```text
endpoint.exe --rpc-url https://your-solana-rpc.example
./endpoint --rpc-url https://your-solana-rpc.example
```

## What “endpoint” means

An endpoint is not a special type of wallet. It is Endpoint's name for the last wallet in the
scanned trail that received a meaningful amount and did not send a meaningful amount onward.

```text
Starting wallet  →  money moves through wallets  →  stopping wallet (the endpoint)
```

It is a lead, not proof of identity or guilt. The **clue strength** number explains how strongly the
observed facts support the result; it is not a percentage chance that the answer is correct.

## What an investigation does

Suppose funds leave one wallet, split across three wallets, and later converge:

```text
Seed wallet
    |-- 18.5 SOL --> Wallet A --\
    |-- 16.0 SOL --> Wallet B ----> Possible consolidation point --> Service
    '-- 15.5 SOL --> Wallet C --/
```

Endpoint turns the observable part of that flow into five simple views:

1. **Answer** - the best stopping wallet, its full address, and three reasons it ranked first.
2. **Wallets found** - the starting wallet and every wallet reached in this scan.
3. **Transactions** - the actual money movements in time order.
4. **Possible links** - investigative clues kept separate from real transfers.
5. **Raw proof** - transaction hashes, blocks or slots, timestamps, amounts, and explorer links.

Clicking a transaction shows its amount, time, signature, and evidence. Clicking a possible link shows
each signal, its exact contribution to the clue-strength score, and the evidence IDs used. Clicking a wallet shows its
observed incoming/outgoing activity and offers a bounded recursive expansion.

## Current capabilities

| Capability | Status | Meaning |
| --- | --- | --- |
| Solana wallet/mint input | Available | Trace a bounded address-referenced transaction slice |
| EVM `0x` wallet input | Available | Ethereum, Base, BNB, Polygon, Arbitrum, Optimism, Avalanche, and Robinhood Chain |
| Robinhood Chain | Available | Native ETH and token transfers from its public Blockscout index |
| BNB Smart Chain | Available | Recent native BNB movements through 3xpl's public BNB index |
| Keyless EVM history | Available | Uses public Routescan, Blockscout, and 3xpl indexes; no user API key needed |
| Real mainnet RPC ingestion | Available | Paces calls, honors `Retry-After`, and preserves partial results |
| SOL transfers | Available | Parses supported System Program transfers |
| SPL-token transfers | Available | Parses supported SPL Token instructions and inner instructions |
| Interactive graph | Available | Pan, zoom, select, and inspect nodes and edges |
| Recursive wallet expansion | Available | Merge another bounded transaction slice into the case |
| Common-funder/timing analysis | Available | Deterministic, evidence-linked heuristics |
| Endpoint ranking | Available | Dust-resistant ranking of meaningful terminal fund flows |
| Local snapshots and JSON export | Available | Persists evidence in SQLite and exports portable JSON |
| Saved-case browser | Planned | Saved snapshots are currently retrievable through the API |
| Synthetic demonstration | Available | Clearly labelled fake data using production analysis code |
| Token-mint rug reconstruction | Planned | Deployer, launch, LP, holder, and post-rug workflow |
| Pump.fun/bundle detection | Planned | Protocol decoding and launch-window coordination signals |
| Historical campaign search | Planned | Requires indexed history and calibrated datasets |
| Cross-chain/bridge correlation | Planned | Requires adapters and explicit uncertainty boundaries |
| Real-world identity attribution | Not a goal | On-chain heuristics do not prove identity |

This is a usable first vertical slice, not a finished commercial intelligence platform. Unsupported
custom-program instructions are never invented or silently presented as decoded transfers.

## Reading the graph safely

Endpoint deliberately separates facts from inference:

| Visual / class | Interpretation |
| --- | --- |
| Solid directed edge / `confirmed_fact` | Money moved in a supported public transaction |
| Possible link | A clue worth checking, not proof that wallets share an owner |
| Diamond node | A possible stopping wallet in this scan |
| Clue strength | Strength of the observed clues, **not** a probability |
| Truncation warning | RPC limits were reached; the result is incomplete |

A shared funder can be an exchange, payroll wallet, airdrop distributor, relayer, or ordinary user.
Convergence can be custody, a service, or routine treasury behavior. These patterns create leads, not
attribution.

See [the scoring methodology](docs/methodology.md) for the exact current formulas and calibration
plan.

## Use the synthetic walkthrough

Choose **Open synthetic demo** on the landing page. It models a seed wallet splitting funds into three
wallets that reconverge before a final transfer. The UI marks the fixture as **not on-chain data**.

Use it to learn the interface:

1. Select a solid arrow and inspect its evidence.
2. Open **Possible links**, select one, and inspect the common-funder/timing clues.
3. Select the diamond wallet and read why it is a consolidation candidate.
4. Compare the language used for a confirmed fact and a heuristic.

The demo exercises the same graph and analysis code as live investigations. Its fake signatures never
enter a production investigation.

## Run with Docker

Docker users can run the source checkout with:

```bash
git clone https://github.com/FiXUnique/endpoint.git
cd endpoint
docker compose up --build
```

Then open `http://localhost:5173`.

## Developer setup

Requirements: Python 3.11+, Node.js 20+, pnpm 11.

```bash
git clone https://github.com/FiXUnique/endpoint.git
cd endpoint

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

corepack enable
pnpm install
pnpm run dev
```

In another terminal:

```bash
uvicorn endpoint.main:app --reload
```

The development UI is at `http://localhost:5173`; API documentation is at
`http://localhost:8000/docs`.

To run the combined production-style application from source:

```bash
pnpm run build
endpoint
```

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health and configuration status |
| `GET /api/v1/networks` | List supported mainnet networks and address formats |
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
  -d '{"chain":"ethereum","address":"0xYOUR_EVM_ADDRESS","signature_limit":25}'
```

## Architecture

```text
React + Cytoscape investigation UI
                |
                | same-origin JSON/HTTP
                v
FastAPI application
    |-- chain-neutral investigation service
    |-- deterministic graph and confidence analysis
    |-- local snapshot repository
    |-- Solana adapter
    |     |-- JSON-RPC retrieval
    |     '-- System/SPL instruction normalization
    '-- EVM adapters
          |-- Routescan, Blockscout, and 3xpl public history
          '-- native/token transfer normalization
```

The packaged executable embeds the production UI and FastAPI service in one local process. Endpoint
listens on loopback by default; live traces make outbound requests only to the configured Solana RPC
or the configured EVM indexer.

Chain-neutral code owns transfers, evidence, cases, graph relationships, limits, and exports.
Chain adapters own address validation, provider semantics, and transfer normalization. EVM networks
use the same `0x` address format, so the selected network is always shown and stored with the case.

Read more:

- [Architecture and hard technical problems](docs/architecture.md)
- [Normalized future data model](docs/data-model.md)
- [Evidence and confidence methodology](docs/methodology.md)
- [Phased roadmap](docs/roadmap.md)
- [Release notes](RELEASE_NOTES.md)

## Known limitations

- The current seed type is a wallet address, not a token mint or transaction signature.
- Only supported `jsonParsed` System/SPL instructions become transfers; opaque custom-program
  semantics are not guessed.
- One expansion fetches a bounded recent signature slice. Endpoint does not yet index full chain
  history.
- Public Solana RPC endpoints frequently rate-limit sustained investigations.
- The same EVM address may have different activity on each network; Endpoint does not assume that
  an Ethereum result also represents Base, BNB Smart Chain, or another EVM chain.
- BNB tracing currently follows native BNB movements. BEP-20 transfer indexing is not yet included.
- Public EVM indexes can rate-limit or omit a newly submitted transaction while it is indexing.
- Token-account ownership depends on transaction token-balance metadata when present.
- Scores are interpretable indices and have not yet been calibrated as probabilities.
- SQLite is appropriate for a local single-user app, not a shared multi-user deployment.
- Packaged binaries are not yet code-signed.

## Verify or contribute

```bash
ruff check .
pytest
pnpm run lint
pnpm test
pnpm run build
```

Heuristic tests assert deterministic formulas, evidence linkage, boundary behavior, and known
ambiguities. They do not treat a heuristic positive as ground-truth wallet ownership.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

[Apache License 2.0](LICENSE). Commercial use and integration are allowed, and contributors receive
explicit patent protection. Commercial derivatives are not required to publish their modifications.
