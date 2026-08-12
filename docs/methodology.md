# Evidence and confidence methodology

Version: `0.1.0`

Endpoint follows: **evidence → relationships → hypotheses → confidence → explanation**.

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

`possible_common_funding_cluster` is emitted when two recipients have a common observed funder:

```text
score = min(1,
  0.45                                             # common funder
  + max(0, 0.20 × (1 - seconds_apart / 120))      # if <= 120 seconds
)
```

The score is deterministic and rounded to four decimals. A common service address can fund unrelated
users, so the result remains a heuristic regardless of score. High-degree known services will be
excluded or separately modelled once the provenance-aware entity registry exists.

## Consolidation candidates

A target observed receiving from at least two distinct graph addresses becomes a *potential
consolidation point*:

```text
score = 0.30 + 0.50 × min(distinct_sources / max_observed_sources, 1)
```

This ranks convergence inside the bounded graph only. It does not establish that the target is an
off-ramp, controls the source wallets, or belongs to a suspect. The UI uses “candidate” and displays
the contributing evidence.

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
