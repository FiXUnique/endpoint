# Security policy

## Reporting

Do not open a public issue for a vulnerability that could expose secrets, corrupt evidence, or enable
denial of service. Use GitHub's private security advisory flow for this repository once published.

## Supported versions

Only the latest release and current default branch receive security fixes during early development.

## Threat model and deployment notes

- Wallet addresses, token metadata, RPC payloads, and investigator notes are untrusted input.
- API keys belong only in backend environment variables; never prefix secrets with `VITE_`.
- The API validates address shape and bounds signature counts. Production deployments should add
  authentication, per-user quotas, request size limits, timeouts, and an outbound RPC allowlist.
- The UI renders labels as React text rather than HTML to prevent metadata-driven XSS.
- CORS defaults to the local UI only. Configure it explicitly in production.
- A malicious or incorrect RPC can manipulate results. Evidence records include RPC provenance;
  future deterministic archives will hash raw responses and support provider comparison.
- SQLite is intended for a trusted single-user local deployment. Multi-user deployments require a
  hardened database, authorization checks, audit logs, encryption/backups, and tenant isolation.

Endpoint never requires wallet keys or signatures. Any distribution requesting them is malicious.
