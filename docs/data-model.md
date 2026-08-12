# Data model

The current API models a normalized subset while the intended relational schema is documented here.
Raw chain data is stored once by `(chain_id, transaction_hash)`; investigation membership points to
global facts rather than copying them.

## Core ledger

- `chains(id, name, network, finality_model)`
- `blocks(id, chain_id, height_or_slot, hash, timestamp)`
- `transactions(id, chain_id, hash, block_id, status, fee, raw_snapshot_ref)`
- `wallets(id, chain_id, address, first_seen_at, last_seen_at)`
- `assets(id, chain_id, address_or_symbol, decimals, metadata_json)`
- `transfers(id, transaction_id, instruction_path, source_wallet_id, target_wallet_id, asset_id,
  raw_amount)`
- `program_interactions(id, transaction_id, wallet_id, protocol_id, program_address,
  instruction_type)`

## Entities and provenance

- `entities(id, category, canonical_name)`
- `labels(id, entity_id, address, source_uri, confidence_class, verified_at, valid_from, valid_to)`
- `protocols(id, chain_id, name, parser_version)`
- `bridges(id, protocol_id, source_chain_id, destination_chain_id)`
- `service_interactions(id, transaction_id, entity_id, interaction_type)`

Labels are claims with provenance and validity windows, not mutable strings on wallet records.

## Investigations

- `investigations(id, title, owner_id, methodology_version, created_at)`
- `investigation_seeds(id, investigation_id, subject_type, subject_id, investigator_note)`
- `graph_nodes(id, investigation_id, subject_type, subject_id, state_json)`
- `graph_edges(id, investigation_id, source_node_id, target_node_id, relationship_id)`
- `clusters(id, investigation_id, algorithm, algorithm_version, label)`
- `cluster_members(cluster_id, wallet_id, membership_score)`
- `notes(id, investigation_id, author_id, body, created_at)`

## Evidence and hypotheses

- `evidence(id, evidence_type, transaction_id, transfer_id, snapshot_hash, retrieved_at, source)`
- `relationships(id, relationship_type, certainty_class, evidence_score, method_version)`
- `relationship_evidence(relationship_id, evidence_id)`
- `confidence_signals(id, relationship_id, signal_type, contribution, explanation, parameters_json)`
- `hypotheses(id, investigation_id, hypothesis_type, status, author_type)`
- `hypothesis_relationships(hypothesis_id, relationship_id)`

Manual notes and hypotheses set `author_type=investigator`; automated conclusions set
`author_type=analysis`. Neither overwrites confirmed ledger facts.

## Current snapshot mapping

The local MVP serializes `InvestigationGraph` to SQLite, containing nodes, edges, evidence, candidates,
limits, and methodology version. The repository interface isolates this implementation so normalized
PostgreSQL storage can replace it without changing the chain adapter or analyzer.
