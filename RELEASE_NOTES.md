# Endpoint v0.1.2

This patch fixes an upgrade problem on desktop: if an older Endpoint process was already listening
on port 8765, launching the new download could leave the browser connected to the old version.

## Fixed in v0.1.2

- Detect when the requested local port is already occupied.
- Start the newly launched version on the next available local port instead of exiting at bind time.
- Open the browser at the port belonging to the new process.
- Print a clear stale-process/port warning in the launcher output.
- Prevent the local browser from caching UI files across packaged versions.
- Catch graph and application rendering failures and show a reload recovery screen instead of a
  black page.
- Show a high-contrast explanation when a transaction slice contains no supported transfers.

## Also included from v0.1.1

This patch turns the first packaged build's display-only surfaces into a usable investigation
workflow and fixes the public Solana RPC failure that caused real traces to abort with HTTP 429.

### Fixed

- Pace Solana JSON-RPC requests below the public endpoint's documented per-method limit.
- Honor numeric `Retry-After` responses with bounded exponential retries.
- Keep successful transaction evidence when individual transaction lookups remain unavailable.
- Report transaction limits, unavailable history, and partial results directly in the case.
- Use Solana's current documented public mainnet endpoint by default.
- Return structured retryable API errors and offer a one-click 10-transaction retry.

### Newly functional

- **Wallets** lists every observed address and opens its evidence inspector.
- **Relationships** lists confirmed and heuristic edges with evidence scores.
- **Timeline** sorts parsed transfers chronologically.
- **Evidence** provides the complete ledger with Solana Explorer verification links.
- Live trace progress and the actual processed/unavailable transaction counts are visible.

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
