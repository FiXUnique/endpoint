# Endpoint v0.3.0

This release makes Endpoint understandable without blockchain vocabulary and adds verified support
for Robinhood Chain while repairing BNB tracing that previously appeared in the menu but failed at
the data provider.

## A clear answer first

- Rename the main sections to **Answer**, **Wallets found**, **Transactions**, **Possible links**,
  and **Raw proof**.
- Define an endpoint directly in the interface as “where the money trail stopped.”
- Show a three-step summary: starting wallet → real transfers → stopping wallet.
- Label the result **Best answer**, keep its full address visible, and provide copy and explorer
  actions.
- Rename evidence scores to **clue strength** and state that the number is not certainty.
- Keep possible wallet links off the default money map so large investigations remain readable.

## Robinhood Chain and BNB

- Add Robinhood Chain mainnet (chain ID 4663) using its public Blockscout index for native ETH and
  token transfers.
- Replace the broken Routescan path for BNB Smart Chain with 3xpl's public BNB index.
- Verify actual indexed histories for both networks and add provider-shaped regression tests.
- BNB tracing currently follows native BNB movements; BEP-20 indexing remains a documented limit.

---

# Endpoint v0.2.0

Endpoint now traces wallet activity across Solana and seven major EVM networks while keeping the
answer focused on the wallet where the observed trail ends.

## Multi-chain address scanning

- Add Ethereum, Base, BNB Smart Chain, Polygon, Arbitrum, Optimism, and Avalanche C-Chain.
- Add an explicit network selector so identical `0x` addresses are never silently mixed across
  chains.
- Retrieve native and ERC-20 transfer history through Routescan's keyless public indexed API.
- Validate addresses according to the selected chain and link every evidence record to the correct
  network explorer.
- Preserve bounded expansion, evidence export, dust resistance, and endpoint ranking on EVM traces.
- Replace deceptive Unicode token symbols with their contract address in the evidence view.

## Clearer endpoint answer

- Put a high-contrast **Endpoint wallet** verdict above the graph.
- Show the full address and add a one-click copy action.
- Explain in plain language that the result is the last observed recipient without later meaningful
  outgoing activity in the scanned data.
- For an empty slice, explicitly say that no endpoint can be identified and remind users to check
  another EVM network.

## Supported networks

Solana, Ethereum, Base, BNB Smart Chain, Polygon, Arbitrum One, Optimism, and Avalanche C-Chain.

---

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
