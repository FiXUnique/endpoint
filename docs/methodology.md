# Evidence and confidence methodology

Version: `0.2.0`

Endpoint follows: **evidence -> relationships -> hypotheses -> confidence -> explanation**.

## Evidence records

Each parsed transfer records chain, signature, slot, timestamp, source, target, asset, amount,
instruction path, RPC source, and retrieval time. The graph uses evidence IDs; explanations cannot
introduce an address or transaction that is absent from those records.

## Certainty classes

- **Confirmed fact:** directly observable in a parsed transaction response.
- **Deterministic relationship:** logically necessary aggregation of confirmed facts.
- **Heuristic relationship:** one or more observable signals support a hypothesis.
- **Weak correlation:** signal exists but is below the configured strength threshold.

No class asserts real-world identity or guilt.

## Current relationship formula

`possible_common_funding_cluster` is emitted when two recipients have a common observed funder.
Probable native-SOL dust transfers at or below `0.00001 SOL` remain in the evidence ledger but do
not create heuristic relationships:

```text
score = min(1,
  0.45                                             # common funder
  + max(0, 0.20 * (1 - seconds_apart / 120))       # if <= 120 seconds
)
```

The score is deterministic and rounded to four decimals. A common service address can fund unrelated
users, so the result remains a heuristic regardless of score. High-degree known services will be
excluded or separately modelled once the provenance-aware entity registry exists.

## Observed endpoint candidates

Endpoint ranking follows meaningful directed transfers outward from the investigation seed. Every
reachable recipient is scored, and terminal wallets (no meaningful outgoing transfer in the current
snapshot) rank ahead of waypoints:

```text
score = min(0.95,
  0.25 if terminal in the observed graph
  + 0.20 if directly funded by the seed
  + 0.20 * min(meaningful_incoming_transfers / 3, 1)
  + 0.25 * strongest per-asset received-value prominence
  + 0.10 * min(distinct_received_assets / 2, 1)
)
```

Per-asset prominence compares a candidate's received total with the largest received total for the
same asset among reachable wallets. It does not compare unrelated token denominations or imply a
fiat value. The `0.00001 SOL` dust rule affects ranking and graph clutter only; every transfer remains
exportable as evidence.

An endpoint means only that the currently observed trail stops at that address. It does not establish
that the wallet is an exchange, off-ramp, final destination, owner of another wallet, or participant
in wrongdoing. Expanding the candidate can reveal later movement and change the ranking.

## Calibration plan

Scores are currently interpretable indices, not calibrated probabilities. Calibration requires:

1. public, provenance-recorded cases with known-positive relationships;
2. hard negatives such as exchange withdrawals, payroll, airdrops, and shared relayers;
3. case-level splitting to prevent wallet/campaign leakage between train and evaluation sets;
4. precision, recall, calibration error, and false-positive analysis per signal family;
5. ablation tests and temporal holdouts;
6. published methodology/version changes.

Tests currently assert determinism, evidence linkage, boundary behavior, and negative/ambiguous
fixtures. They never treat an unverified heuristic result as ground-truth ownership.

## Privacy systems and bridges

Neither is implemented in the MVP. Future privacy-service interactions create uncertainty boundaries,
not invisible deterministic edges. Bridge correlations must preserve source and destination evidence,
fee/amount models, time ranges, competing candidates, and a statement of what cannot be observed.
