import {
  Component,
  lazy,
  Suspense,
  useMemo,
  useState,
  type ErrorInfo,
  type ReactNode,
} from "react";

import type { ExitCandidate, GraphEdge, Investigation, Selection } from "../types";

const GraphCanvas = lazy(async () => {
  const module = await import("./GraphCanvas");
  return { default: module.GraphCanvas };
});

class GraphErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[endpoint:graph] renderer failed", error, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="workspace-result-message graph-error" role="alert">
          <strong>The graph could not be displayed</strong>
          <p>Your investigation data is safe. Reload Endpoint or use Wallets, Relationships, Timeline, and Evidence in the sidebar.</p>
          <button onClick={() => window.location.reload()}>Reload Endpoint</button>
        </div>
      );
    }
    return this.props.children;
  }
}

export type InvestigationSection =
  | "fund-flow"
  | "wallets"
  | "relationships"
  | "timeline"
  | "evidence";

interface InvestigationWorkspaceProps {
  investigation: Investigation;
  section: InvestigationSection;
  onSelect: (selection: Selection) => void;
}

const SECTION_TITLES: Record<InvestigationSection, string> = {
  "fund-flow": "Fund-flow graph",
  wallets: "Observed wallets",
  relationships: "Evidence-backed relationships",
  timeline: "Transaction timeline",
  evidence: "Evidence ledger",
};

function short(value: string): string {
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function assetName(asset: string): string {
  if (asset === "SOL") return "SOL";
  if (asset === "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v") return "USDC";
  if (asset === "So11111111111111111111111111111111111111112") return "wrapped SOL";
  return `${asset.slice(0, 5)}...${asset.slice(-4)}`;
}

function EndpointAnswer({
  investigation,
  candidate,
  onSelect,
}: {
  investigation: Investigation;
  candidate: ExitCandidate;
  onSelect: (selection: Selection) => void;
}) {
  const node = investigation.nodes.find((item) => item.address === candidate.address);
  return (
    <section className="endpoint-answer" aria-label="Likely endpoint">
      <div className="endpoint-answer-heading">
        <div>
          <span className="eyebrow">Likely endpoint in this trace</span>
          <h2>{short(candidate.address)}</h2>
          <code title={candidate.address}>{candidate.address}</code>
        </div>
        <div className="endpoint-confidence">
          <strong>{Math.round(candidate.evidence_score * 100)}</strong>
          <span>evidence score</span>
        </div>
      </div>
      <div className="endpoint-reasons">
        <div><span>1</span><p><strong>Funds arrived here</strong>{candidate.received_assets.map((total) => `${total.amount} ${assetName(total.asset)}`).join(" + ")}</p></div>
        <div><span>2</span><p><strong>The observed trail {candidate.terminal_in_observed_graph ? "stops here" : "continues"}</strong>{candidate.terminal_in_observed_graph ? "No meaningful outgoing transfer appears in this snapshot." : `${candidate.outgoing_transfer_count} meaningful outgoing transfer(s) appear in this snapshot.`}</p></div>
        <div><span>3</span><p><strong>{candidate.hop_distance === 1 ? "Directly from the seed" : `${candidate.hop_distance ?? "?"} hops from the seed`}</strong>{candidate.incoming_transfer_count} meaningful incoming transfer{candidate.incoming_transfer_count === 1 ? "" : "s"}; dust is excluded from this ranking.</p></div>
      </div>
      <div className="endpoint-answer-footer">
        <p>This is where the currently observed trail ends, not an identity or ownership claim.</p>
        {node && <button onClick={() => onSelect({ kind: "node", value: node })}>Inspect and continue tracing</button>}
      </div>
    </section>
  );
}

function sectionCount(investigation: Investigation, section: InvestigationSection): string {
  const meaningfulEdges = investigation.edges.filter((edge) => !edge.probable_noise);
  if (section === "fund-flow") {
    const visibleNodes = new Set([
      investigation.seed,
      ...meaningfulEdges.flatMap((edge) => [edge.source, edge.target]),
    ]);
    return `${visibleNodes.size} wallets · ${meaningfulEdges.length} meaningful relationships`;
  }
  if (section === "wallets") return `${investigation.nodes.length} observed addresses`;
  if (section === "relationships") return `${meaningfulEdges.length} meaningful relationships`;
  return `${investigation.evidence.length} evidence records`;
}

function WalletList({ investigation, onSelect }: Omit<InvestigationWorkspaceProps, "section">) {
  return (
    <div className="record-list" aria-label="Observed wallets">
      {investigation.nodes.map((node) => (
        <button
          className="record-row wallet-record"
          key={node.id}
          onClick={() => onSelect({ kind: "node", value: node })}
        >
          <span className={`record-marker ${node.seed ? "seed" : "wallet"}`} />
          <div>
            <strong>{node.seed ? "Investigation seed" : node.label ?? "Observed address"}</strong>
            <code title={node.address}>{short(node.address)}</code>
          </div>
          <span>{node.incoming_count} in</span>
          <span>{node.outgoing_count} out</span>
          <span>{node.observed_assets.length} assets</span>
        </button>
      ))}
    </div>
  );
}

function RelationshipList({
  investigation,
  onSelect,
}: Omit<InvestigationWorkspaceProps, "section">) {
  return (
    <div className="record-list" aria-label="Relationships">
      {investigation.edges.filter((edge) => !edge.probable_noise).map((edge) => (
        <button
          className="record-row relationship-record"
          key={edge.id}
          onClick={() => onSelect({ kind: "edge", value: edge })}
        >
          <span
            className={`record-marker ${
              edge.certainty === "confirmed_fact" ? "confirmed" : "heuristic"
            }`}
          />
          <div>
            <strong>{edge.relationship.replaceAll("_", " ")}</strong>
            <code>{short(edge.source)} → {short(edge.target)}</code>
          </div>
          <span>{edge.label}</span>
          <b>{Math.round(edge.evidence_score * 100)}/100</b>
        </button>
      ))}
    </div>
  );
}

function EvidenceRows({
  investigation,
  onSelect,
  timeline,
}: Omit<InvestigationWorkspaceProps, "section"> & { timeline: boolean }) {
  const [showNoise, setShowNoise] = useState(false);
  const edgeByEvidenceId = useMemo(() => {
    const index = new Map<string, GraphEdge>();
    for (const edge of investigation.edges) {
      for (const evidenceId of edge.evidence_ids) index.set(evidenceId, edge);
    }
    return index;
  }, [investigation.edges]);
  const evidence = [...investigation.evidence].sort((left, right) => {
    if (left.timestamp && right.timestamp) {
      return new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime();
    }
    return right.slot - left.slot;
  });
  const noiseEvidence = evidence.filter(
    (item) => edgeByEvidenceId.get(item.id)?.probable_noise,
  );
  const visibleEvidence = showNoise
    ? evidence
    : evidence.filter((item) => !edgeByEvidenceId.get(item.id)?.probable_noise);
  if (!evidence.length) {
    return <div className="workspace-empty">No parsed transfer evidence was found in this slice.</div>;
  }
  return (
    <div className="record-list" aria-label={timeline ? "Transaction timeline" : "Evidence ledger"}>
      {!!noiseEvidence.length && (
        <div className="noise-summary">
          <div>
            <strong>{noiseEvidence.length} probable dust transfer{noiseEvidence.length === 1 ? "" : "s"} hidden</strong>
            <span>Still preserved in the evidence export.</span>
          </div>
          <button onClick={() => setShowNoise((current) => !current)}>
            {showNoise ? "Hide dust" : "Show dust"}
          </button>
        </div>
      )}
      {visibleEvidence.map((item) => {
        const edge = edgeByEvidenceId.get(item.id);
        return (
          <div className="record-row evidence-record" key={item.id}>
            <span className="record-marker confirmed" />
            <button onClick={() => edge && onSelect({ kind: "edge", value: edge })}>
              <strong>{item.amount} {item.asset}</strong>
              <code>{short(item.source)} → {short(item.target)}</code>
            </button>
            <span>{item.timestamp ? new Date(item.timestamp).toLocaleString() : `slot ${item.slot.toLocaleString()}`}</span>
            <a
              href={`https://explorer.solana.com/tx/${item.signature}`}
              target="_blank"
              rel="noreferrer"
              title="Open transaction in Solana Explorer"
            >
              Verify ↗
            </a>
          </div>
        );
      })}
    </div>
  );
}

export function InvestigationWorkspace({
  investigation,
  section,
  onSelect,
}: InvestigationWorkspaceProps) {
  const meaningfulEdges = investigation.edges.filter((edge) => !edge.probable_noise);
  const hasRelationships = meaningfulEdges.length > 0;
  const primaryEndpoint = investigation.exit_candidates[0];
  return (
    <section className="workspace">
      <div className="workspace-toolbar">
        <div>
          <span className="eyebrow">{SECTION_TITLES[section]}</span>
          <strong>{sectionCount(investigation, section)}</strong>
        </div>
        <div className="toolbar-chips">
          <span>1 hop per expansion</span>
          <span>{investigation.limits.processed_transactions ?? investigation.limits.returned_signatures} inspected</span>
          {!!investigation.limits.failed_transactions && (
            <span className="warning-chip">{investigation.limits.failed_transactions} unavailable</span>
          )}
        </div>
      </div>
      {section === "fund-flow" && !hasRelationships && (
        <div className="workspace-result-message" role="status">
          <span className="result-glyph">0</span>
          <strong>No supported transfers in this transaction slice</strong>
          <p>
            Endpoint reached Solana and inspected {investigation.limits.processed_transactions ?? investigation.limits.returned_signatures} transactions, but none contained parsed SOL or SPL-token transfers it can graph.
          </p>
          <p>Try a different wallet, raise the transaction limit, or inspect Wallets and Evidence.</p>
        </div>
      )}
      {section === "fund-flow" && hasRelationships && (
        <>
          {primaryEndpoint && (
            <EndpointAnswer
              investigation={investigation}
              candidate={primaryEndpoint}
              onSelect={onSelect}
            />
          )}
          <GraphErrorBoundary>
            <Suspense fallback={<div className="graph-loading">Preparing graph renderer...</div>}>
              <GraphCanvas investigation={investigation} onSelect={onSelect} />
            </Suspense>
          </GraphErrorBoundary>
        </>
      )}
      {section === "wallets" && <WalletList investigation={investigation} onSelect={onSelect} />}
      {section === "relationships" && (
        <RelationshipList investigation={investigation} onSelect={onSelect} />
      )}
      {section === "timeline" && (
        <EvidenceRows investigation={investigation} onSelect={onSelect} timeline />
      )}
      {section === "evidence" && (
        <EvidenceRows investigation={investigation} onSelect={onSelect} timeline={false} />
      )}
    </section>
  );
}
