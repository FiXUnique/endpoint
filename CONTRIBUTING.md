# Contributing

Thanks for helping make public-chain investigations more reproducible and less speculative.

1. Open an issue describing the evidence source, behavior, and scope.
2. Create a focused branch and add deterministic fixtures.
3. Keep chain-specific decoding inside `backend/endpoint/chains` or a protocol parser package.
4. Every inferred relationship must identify evidence, a versioned formula, and limitations.
5. Run `ruff check .`, `pytest`, `pnpm run lint`, `pnpm test`, and `pnpm run build`.
6. Describe false-positive risks in the pull request.

Do not submit private attribution datasets, personal information, private keys, exploit automation,
wallet-draining behavior, or claims of identity/guilt unsupported by independently verified sources.

For new heuristics, include positive, hard-negative, boundary, and missing-data fixtures. Prefer a
small explainable signal over an opaque score.
