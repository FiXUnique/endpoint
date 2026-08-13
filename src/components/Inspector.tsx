import type { Evidence, Investigation, Selection } from "../types";

interface InspectorProps {
  investigation: Investigation;
  selection: Selection;
  expanding: boolean;
  onExpand: (address: string) => void;
}

function short(value: string): string {
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function assetName(asset: string): string {
  if (asset === "SOL") return "SOL";
  if (asset === "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v") return "USDC";
  if (asset.length <= 18) return asset;
  return `${asset.slice(0, 5)}...${asset.slice(-4)}`;
}

function EvidenceList({ items }: { items: Evidence[] }) {
  if (!items.length) return <p className="muted">No evidence references attached.</p>;
  return (
    <div className="evidence-list">
      {items.map((item) => (
        <article className="evidence-item" key={item.id}>
          <div className="evidence-topline">
            <span className="status-dot confirmed" />
            <strong>{item.amount} {item.asset}</strong>
            <span>{item.chain === "solana" ? "slot" : "block"} {item.slot.toLocaleString()}</span>
          </div>
          <code title={item.signature}>{short(item.signature)}</code>
          <time>{item.timestamp ? new Date(item.timestamp).toLocaleString() : "Timestamp unavailable"}</time>
        </article>
      ))}
    </div>
  );
}

export function Inspector({ investigation, selection, expanding, onExpand }: InspectorProps) {
  if (!selection) {
    return (
      <aside className="inspector empty-state">
        <div className="empty-glyph">⌖</div>
        <h2>Inspect the evidence</h2>
        <p>Select any node or relationship to see the exact transactions and reasoning behind it.</p>
      </aside>
    );
  }

  if (selection.kind === "node") {
    const node = selection.value;
    const nodeEvidence = investigation.evidence.filter(
      (item) => item.source === node.address || item.target === node.address,
    );
    const candidate = investigation.exit_candidates.find((item) => item.address === node.address);
    return (
      <aside className="inspector">
        <div className="inspector-heading">
          <div>
            <span className="eyebrow">Selected wallet</span>
            <h2>{node.seed ? "Investigation seed" : "Observed address"}</h2>
          </div>
          <span className={`certainty-pill ${node.seed ? "confirmed" : "observed"}`}>
            {node.seed ? "seed" : "observed"}
          </span>
        </div>
        <code className="address-block">{node.address}</code>
        <div className="metric-row">
          <div><span>Incoming</span><strong>{node.incoming_count}</strong></div>
          <div><span>Outgoing</span><strong>{node.outgoing_count}</strong></div>
          <div><span>Assets</span><strong>{node.observed_assets.length}</strong></div>
        </div>
        {candidate && (
          <div className="endpoint-inspector-card">
            <span className="eyebrow">
              {candidate.terminal_in_observed_graph ? "Likely endpoint" : "Fund-flow waypoint"}
            </span>
            <strong>{Math.round(candidate.evidence_score * 100)}/100 evidence score</strong>
            <p className="endpoint-assets">
              Received: {candidate.received_assets.map((total) => `${total.amount} ${assetName(total.asset)}`).join(" + ")}
            </p>
            <p>{candidate.explanation}</p>
          </div>
        )}
        <button
          className="secondary-button expand-button"
          disabled={expanding || investigation.data_source === "synthetic_demo"}
          onClick={() => onExpand(node.address)}
        >
          {expanding ? "Expanding…" : "Expand wallet · 15 transactions"}
        </button>
        {investigation.data_source === "synthetic_demo" && (
          <p className="field-note">Expansion is disabled for the synthetic demonstration.</p>
        )}
        <section className="inspector-section">
          <div className="section-title"><h3>Referenced evidence</h3><span>{nodeEvidence.length}</span></div>
          <EvidenceList items={nodeEvidence} />
        </section>
      </aside>
    );
  }

  const edge = selection.value;
  const edgeEvidence = investigation.evidence.filter((item) => edge.evidence_ids.includes(item.id));
  const isFact = edge.certainty === "confirmed_fact";
  return (
    <aside className="inspector">
      <div className="inspector-heading">
        <div>
          <span className="eyebrow">Selected relationship</span>
          <h2>{edge.relationship.replaceAll("_", " ")}</h2>
        </div>
        <span className={`certainty-pill ${isFact ? "confirmed" : "heuristic"}`}>
          {isFact ? "confirmed fact" : "heuristic"}
        </span>
      </div>
      <div className="score-panel">
        <div>
          <span>Evidence score</span>
          <strong>{Math.round(edge.evidence_score * 100)}<small>/100</small></strong>
        </div>
        <p>{isFact ? "Parsed directly from public on-chain transaction instructions." : "A reproducible heuristic score, not a probability of common ownership."}</p>
      </div>
      <section className="inspector-section">
        <div className="section-title"><h3>Why this relationship appears</h3><span>{edge.signals.length}</span></div>
        <div className="signal-list">
          {edge.signals.map((signal) => (
            <div className="signal" key={`${edge.id}-${signal.type}`}>
              <span className={`status-dot ${isFact ? "confirmed" : "heuristic"}`} />
              <div><strong>{signal.type.replaceAll("_", " ")}</strong><p>{signal.explanation}</p></div>
              <b>+{Math.round(signal.contribution * 100)}</b>
            </div>
          ))}
        </div>
      </section>
      <section className="inspector-section">
        <div className="section-title"><h3>Referenced evidence</h3><span>{edgeEvidence.length}</span></div>
        <EvidenceList items={edgeEvidence} />
      </section>
    </aside>
  );
}
