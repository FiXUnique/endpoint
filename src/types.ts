export type Certainty =
  | "confirmed_fact"
  | "deterministic_relationship"
  | "heuristic_relationship"
  | "weak_correlation";

export interface Signal {
  type: string;
  contribution: number;
  explanation: string;
  evidence_ids: string[];
}

export interface GraphNode {
  id: string;
  address: string;
  kind: "wallet" | "token_account" | "program" | "unknown";
  label: string | null;
  seed: boolean;
  incoming_count: number;
  outgoing_count: number;
  observed_assets: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  certainty: Certainty;
  evidence_score: number;
  label: string;
  asset: string | null;
  amount: string | null;
  transfer_count: number;
  signals: Signal[];
  evidence_ids: string[];
}

export interface Evidence {
  id: string;
  chain: string;
  signature: string;
  slot: number;
  timestamp: string | null;
  source: string;
  target: string;
  asset: string;
  amount: string;
  instruction_path: string;
  rpc_url: string | null;
  retrieved_at: string;
}

export interface ExitCandidate {
  address: string;
  evidence_score: number;
  label: string;
  explanation: string;
  contributing_wallets: number;
  evidence_ids: string[];
}

export interface Investigation {
  investigation_id: string;
  name: string;
  chain: string;
  seed: string;
  data_source: "live_rpc" | "synthetic_demo";
  created_at: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  evidence: Evidence[];
  exit_candidates: ExitCandidate[];
  limits: {
    requested_signatures: number;
    returned_signatures: number;
    processed_transactions?: number;
    failed_transactions?: number;
    truncated: boolean;
    notice: string | null;
  };
  methodology_version: string;
}

export type Selection =
  | { kind: "node"; value: GraphNode }
  | { kind: "edge"; value: GraphEdge }
  | null;
