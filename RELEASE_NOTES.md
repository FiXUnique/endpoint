# Endpoint v0.1.0

Endpoint's first packaged release provides an evidence-first Solana wallet investigation workflow.

## Download and run

### Windows

1. Download `endpoint-windows-x64.zip`.
2. Extract the archive.
3. Double-click `endpoint.exe`.
4. Your browser opens to the local Endpoint application.

Windows SmartScreen may show an “unrecognized app” warning because this open-source binary is not
code-signed yet. Choose **More info → Run anyway** only if the download came from this repository's
official GitHub Releases page.

### Linux

1. Download and extract `endpoint-linux-x64.tar.gz`.
2. Run `./endpoint` from the extracted folder.
3. Open `http://127.0.0.1:8765` if the browser does not open automatically.

No Python, Node.js, database server, or Docker installation is required for these packaged builds.

## Included workflow

- Trace a Solana wallet's recent real mainnet transactions.
- Normalize observed SOL and SPL-token transfer instructions.
- Explore transfers in an interactive fund-flow graph.
- Expand downstream or upstream wallets with bounded RPC requests.
- Inspect the exact signature, slot, time, value, and instruction behind a transfer.
- Review clearly marked common-funder and timing heuristics.
- Rank possible consolidation points without presenting them as proven exit wallets.
- Save investigation snapshots locally and export evidence as JSON.
- Open a synthetic example that is unmistakably labelled as non-chain data.

## Data and network behavior

Endpoint listens only on `127.0.0.1:8765` by default. Investigation snapshots are stored in the
current user's application-data directory. Live traces query the configured Solana JSON-RPC endpoint;
public RPC endpoints may rate-limit larger investigations.

This release does not identify people, prove wallet ownership, or determine guilt. Heuristic evidence
scores are reproducible indices—not probabilities of common ownership.
