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
  "fund-flow": "Your answer",
  wallets: "Wallets Endpoint found",
  relationships: "Possible links — clues, not proof",
  timeline: "Money movements",
  evidence: "Raw blockchain proof",
};

function short(value: string): string {
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function assetName(asset: string): string {
  if (asset === "SOL") return "SOL";
  if (asset === "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v") return "USDC";
  if (asset === "So11111111111111111111111111111111111111112") return "wrapped SOL";
  if (asset.length <= 18) return asset;
  return `${asset.slice(0, 5)}...${asset.slice(-4)}`;
}

const EXPLORERS: Record<string, string> = {
  solana: "https://explorer.solana.com/tx/",
  ethereum: "https://etherscan.io/tx/",
  base: "https://basescan.org/tx/",
  bnb: "https://bscscan.com/tx/",
  polygon: "https://polygonscan.com/tx/",
  arbitrum: "https://arbiscan.io/tx/",
  optimism: "https://optimistic.etherscan.io/tx/",
  avalanche: "https://snowtrace.io/tx/",
  robinhood: "https://robinhoodchain.blockscout.com/tx/",
};

const ADDRESS_EXPLORERS: Record<string, string> = {
  solana: "https://explorer.solana.com/address/",
  ethereum: "https://etherscan.io/address/",
  base: "https://basescan.org/address/",
  bnb: "https://bscscan.com/address/",
  polygon: "https://polygonscan.com/address/",
  arbitrum: "https://arbiscan.io/address/",
  optimism: "https://optimistic.etherscan.io/address/",
  avalanche: "https://snowtrace.io/address/",
  robinhood: "https://robinhoodchain.blockscout.com/address/",
};

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
  const [copied, setCopied] = useState(false);
  const confirmedTransfers = investigation.edges.filter(
    (edge) => edge.certainty === "confirmed_fact" && !edge.probable_noise,
  ).length;

  async function copyEndpoint() {
    try {
      await navigator.clipboard.writeText(candidate.address);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }
  return (
    <section className="endpoint-answer" aria-label="Likely endpoint">
      <div className="endpoint-answer-heading">
        <div>
          <span className="endpoint-verdict">Best answer</span>
          <span className="eyebrow">Endpoint means “where the money trail stopped”</span>
          <h2>The money trail stops at this wallet</h2>
          <code title={candidate.address}>{candidate.address}</code>
        </div>
        <div className="endpoint-confidence">
          <strong>{Math.round(candidate.evidence_score * 100)}</strong>
          <span>clue strength / 100</span>
        </div>
      </div>
      <div className="trail-steps" aria-label="Simple money trail">
        <div><span>1</span><small>Started at</small><code>{short(investigation.seed)}</code></div>
        <i>→</i>
        <div><span>2</span><small>Endpoint followed</small><strong>{confirmedTransfers} real transfer{confirmedTransfers === 1 ? "" : "s"}</strong></div>
        <i>→</i>
        <div className="trail-stop"><span>3</span><small>Stopped at</small><code>{short(candidate.address)}</code></div>
      </div>
      <div className="endpoint-reasons">
        <div><span>✓</span><p><strong>Money arrived</strong>{candidate.received_assets.map((total) => `${total.amount} ${assetName(total.asset)}`).join(" + ")}</p></div>
        <div><span>✓</span><p><strong>{candidate.terminal_in_observed_graph ? "No money moved onward" : "Some money moved onward"}</strong>{candidate.terminal_in_observed_graph ? "No meaningful outgoing transfer was found in this scan." : `${candidate.outgoing_transfer_count} outgoing transfer(s) were found.`}</p></div>
        <div><span>✓</span><p><strong>{candidate.hop_distance === 1 ? "One step from the start" : `${candidate.hop_distance ?? "?"} steps from the start`}</strong>Tiny spam and dust transfers are ignored.</p></div>
      </div>
      <div className="endpoint-answer-footer">
        <p>Clue strength is not certainty, and this result does not identify who owns the wallet.</p>
        <div>
          <button onClick={() => void copyEndpoint()}>{copied ? "Copied" : "Copy wallet"}</button>
          <a href={`${ADDRESS_EXPLORERS[investigation.chain] ?? ADDRESS_EXPLORERS.ethereum}${candidate.address}`} target="_blank" rel="noreferrer">Open in explorer ↗</a>
          {node && <button onClick={() => onSelect({ kind: "node", value: node })}>See wallet details</button>}
        </div>
      </div>
    </section>
  );
}

function sectionCount(investigation: Investigation, section: InvestigationSection): string {
  const meaningfulEdges = investigation.edges.filter((edge) => !edge.probable_noise);
  if (section === "fund-flow") {
    const confirmedEdges = meaningfulEdges.filter((edge) => edge.certainty === "confirmed_fact");
    const visibleNodes = new Set([
      investigation.seed,
      ...confirmedEdges.flatMap((edge) => [edge.source, edge.target]),
    ]);
    return `${visibleNodes.size} wallets · ${confirmedEdges.length} real transfers`;
  }
  if (section === "wallets") return `${investigation.nodes.length} observed addresses`;
  if (section === "relationships") return `${meaningfulEdges.filter((edge) => edge.certainty !== "confirmed_fact").length} possible links`;
  return `${investigation.evidence.length} blockchain records`;
}

function WalletList({ investigation, onSelect }: Omit<InvestigationWorkspaceProps, "section">) {
  return (
    <div className="record-list" aria-label="Wallets found">
      {investigation.nodes.map((node) => (
        <button
          className="record-row wallet-record"
          key={node.id}
          onClick={() => onSelect({ kind: "node", value: node })}
        >
          <span className={`record-marker ${node.seed ? "seed" : "wallet"}`} />
          <div>
            <strong>{node.seed ? "Starting wallet" : node.label ?? "Wallet found"}</strong>
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
  const possibleLinks = investigation.edges.filter(
    (edge) => edge.certainty !== "confirmed_fact" && !edge.probable_noise,
  );
  if (!possibleLinks.length) {
    return <div className="workspace-empty">No extra wallet links were suggested. Real transfers are shown under Answer and Transactions.</div>;
  }
  return (
    <div className="record-list" aria-label="Possible links">
      {possibleLinks.map((edge) => (
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
            <strong>Possible link: {edge.relationship.replaceAll("_", " ")}</strong>
            <code>{short(edge.source)} → {short(edge.target)}</code>
          </div>
          <span>{edge.label}</span>
          <b title="Clue strength, not certainty">{Math.round(edge.evidence_score * 100)}/100</b>
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
    <div className="record-list" aria-label={timeline ? "Transactions" : "Raw proof"}>
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
              href={`${EXPLORERS[investigation.chain] ?? EXPLORERS.ethereum}${item.signature}`}
              target="_blank"
              rel="noreferrer"
              title="Open transaction in the network explorer"
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
  const hasTransfers = meaningfulEdges.some((edge) => edge.certainty === "confirmed_fact");
  const primaryEndpoint = investigation.exit_candidates[0];
  return (
    <section className="workspace">
      <div className="workspace-toolbar">
        <div>
          <span className="eyebrow">{SECTION_TITLES[section]}</span>
          <strong>{sectionCount(investigation, section)}</strong>
        </div>
        <div className="toolbar-chips">
          <span>One wallet step at a time</span>
          <span>{investigation.limits.processed_transactions ?? investigation.limits.returned_signatures} transactions checked</span>
          {!!investigation.limits.failed_transactions && (
            <span className="warning-chip">{investigation.limits.failed_transactions} unavailable</span>
          )}
        </div>
      </div>
      {section === "fund-flow" && !hasTransfers && (
        <div className="workspace-result-message" role="status">
          <span className="result-glyph">0</span>
          <strong>No money trail was found in this scan</strong>
          <p>
            Endpoint checked {investigation.limits.processed_transactions ?? investigation.limits.returned_signatures} transactions on {investigation.chain}, but found no supported money transfers to follow.
          </p>
          <p>There is no stopping wallet to show yet. If this is a 0x address, try another network—the same wallet address can exist on several chains.</p>
        </div>
      )}
      {section === "fund-flow" && hasTransfers && (
        <>
          {primaryEndpoint && (
            <EndpointAnswer
              investigation={investigation}
              candidate={primaryEndpoint}
              onSelect={onSelect}
            />
          )}
          <div className="map-intro"><strong>Money map</strong><span>Only real transfers are drawn here. Possible links stay in their own section so this map remains readable.</span></div>
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
