# Endpoint v0.1.3

This release makes the result understandable without requiring users to interpret hundreds of raw
wallet and relationship rows.

## Clear endpoint answer

- Put one **Likely endpoint in this trace** answer above the graph.
- Show the complete wallet address, received asset totals, hop distance, evidence score, and the
  exact reasons it ranked first.
- Automatically select the likely endpoint so its evidence and expansion action are immediately
  visible.
- Rename the confusing consolidation list to **Endpoint candidates** and state whether funds stop
  or continue at each wallet.

## Dust-resistant analysis

- Preserve tiny transfers in the evidence ledger and JSON export while excluding probable SOL dust
  from endpoint ranking and common-funder relationships.
- Follow meaningful transfers outward from the seed instead of ranking unrelated inbound activity.
- Rank observed terminal wallets using transfer repetition, asset breadth, direct seed funding, and
  per-asset value prominence.
- Hide probable dust from the graph, relationship list, and timeline by default, with a **Show dust**
  control for reviewers who need it.
- Reduce a verified dust-poisoned trace from thousands of noisy combinations to a compact meaningful
  graph and correctly rank its high-value terminal wallet first.

## Reliability retained

- Includes the prior RPC retry/rate-limit handling, stale-port fallback, no-cache desktop UI,
  rendering recovery screens, evidence export, and functional investigation views.

## Download and run

### Windows

1. Download `endpoint-windows-x64.zip`.
2. Extract the archive.
3. Double-click `endpoint.exe`.
4. Your browser opens to `http://127.0.0.1:8765`.

Windows SmartScreen may show an "unrecognized app" warning because this open-source binary is not
code-signed. Only run a binary downloaded from this repository's official Releases page.

### Linux

1. Download and extract `endpoint-linux-x64.tar.gz`.
2. Run `./endpoint` from the extracted folder.
3. Open `http://127.0.0.1:8765` if the browser does not open automatically.

No Python, Node.js, database server, or Docker installation is required.

## RPC note

Solana's public endpoint is explicitly rate-limited and not intended as production infrastructure.
Endpoint now slows down and retries correctly, but large or repeated investigations should use a
dedicated provider:

```text
endpoint.exe --rpc-url https://your-solana-rpc.example
./endpoint --rpc-url https://your-solana-rpc.example
```

Endpoint does not identify people, prove wallet ownership, or determine guilt. Evidence scores are
reproducible indices, not probabilities of common ownership.
