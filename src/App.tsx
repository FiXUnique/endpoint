import { useCallback, useState, type FormEvent } from "react";

import { ApiError, expandAddress, exportUrl, loadDemo, traceAddress } from "./api";
import { Inspector } from "./components/Inspector";
import {
  InvestigationWorkspace,
  type InvestigationSection,
} from "./components/InvestigationWorkspace";
import type { Investigation, Selection } from "./types";

function shortAddress(value: string): string {
  return `${value.slice(0, 6)}…${value.slice(-5)}`;
}

interface DisplayError {
  message: string;
  retryable: boolean;
}

function displayError(error: unknown, fallback: string): DisplayError {
  return {
    message: error instanceof Error ? error.message : fallback,
    retryable: error instanceof ApiError && error.retryable,
  };
}

export default function App() {
  const [address, setAddress] = useState("");
  const [limit, setLimit] = useState(25);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [section, setSection] = useState<InvestigationSection>("fund-flow");
  const [loading, setLoading] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [error, setError] = useState<DisplayError | null>(null);

  const select = useCallback((next: Selection) => setSelection(next), []);

  async function executeTrace(signatureLimit = limit) {
    if (!address.trim()) return;
    setLoading(true);
    setError(null);
    setSelection(null);
    try {
      setInvestigation(await traceAddress(address.trim(), signatureLimit));
      setSection("fund-flow");
    } catch (requestError) {
      setError(displayError(requestError, "Investigation failed"));
    } finally {
      setLoading(false);
    }
  }

  async function runTrace(event: FormEvent) {
    event.preventDefault();
    await executeTrace();
  }

  async function openDemo() {
    setLoading(true);
    setError(null);
    setSelection(null);
    try {
      setInvestigation(await loadDemo());
      setSection("fund-flow");
    } catch (requestError) {
      setError(displayError(requestError, "Demo failed to load"));
    } finally {
      setLoading(false);
    }
  }

  async function expand(addressToExpand: string) {
    if (!investigation) return;
    setExpanding(true);
    setError(null);
    try {
      const updated = await expandAddress(investigation.investigation_id, addressToExpand);
      setInvestigation(updated);
      setSelection({
        kind: "node",
        value: updated.nodes.find((node) => node.address === addressToExpand) ?? updated.nodes[0],
      });
    } catch (requestError) {
      setError(displayError(requestError, "Expansion failed"));
    } finally {
      setExpanding(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">E<span>·</span></span>
          <div><strong>endpoint</strong><small>ON-CHAIN FORENSICS</small></div>
        </div>
        <form className="search-form" onSubmit={runTrace}>
          <span className="search-icon">⌕</span>
          <input
            aria-label="Solana wallet or mint address"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="Search a Solana wallet or mint address"
            minLength={32}
            maxLength={44}
          />
          <select
            aria-label="Transaction limit"
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          >
            <option value={10}>10 txs</option>
            <option value={25}>25 txs</option>
            <option value={50}>50 txs</option>
          </select>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? "Analyzing…" : "Trace funds"}
          </button>
        </form>
        <div className="network-state"><span /> Solana mainnet</div>
      </header>

      {loading && (
        <div className="progress-banner" role="status">
          <span /> Fetching and parsing public Solana transactions. Rate-limit retries may take a moment.
        </div>
      )}
      {error && (
        <div className="error-banner" role="alert">
          <strong>Analysis error</strong>
          <span>{error.message}</span>
          {error.retryable && address.trim() && (
            <button
              className="retry-button"
              onClick={() => {
                setLimit(10);
                void executeTrace(10);
              }}
            >
              Retry with 10 txs
            </button>
          )}
          <button
            className="dismiss-button"
            aria-label="Dismiss error"
            onClick={() => setError(null)}
          >
            ×
          </button>
        </div>
      )}

      {!investigation ? (
        <main className="welcome">
          <div className="welcome-grid" />
          <section className="welcome-copy">
            <div className="kicker"><span /> EVIDENCE BEFORE INFERENCE</div>
            <h1>Follow the money.<br /><em>Question the conclusion.</em></h1>
            <p>Trace public Solana transfers, inspect every relationship, and distinguish on-chain facts from reproducible heuristics.</p>
            <div className="welcome-actions">
              <button className="primary-button large" onClick={() => document.querySelector<HTMLInputElement>(".search-form input")?.focus()}>Start with an address</button>
              <button className="secondary-button large" disabled={loading} onClick={openDemo}>Open synthetic demo</button>
            </div>
            <div className="trust-row">
              <span><b>01</b> Public data only</span>
              <span><b>02</b> Evidence-linked</span>
              <span><b>03</b> No identity claims</span>
            </div>
          </section>
          <aside className="method-card">
            <span className="eyebrow">Method</span>
            <div className="method-flow"><b>Evidence</b><i>→</i><b>Relationships</b><i>→</i><b>Hypotheses</b></div>
            <p>Endpoint never turns correlation into certainty. Heuristic relationships remain dashed, scored, and explainable.</p>
            <div className="method-rule"><span className="status-dot confirmed" /><div><strong>Confirmed fact</strong><small>Directly parsed from a transaction</small></div></div>
            <div className="method-rule"><span className="status-dot heuristic" /><div><strong>Heuristic relationship</strong><small>Reproducible signals, not attribution</small></div></div>
          </aside>
        </main>
      ) : (
        <main className="investigation-layout">
          <aside className="case-sidebar">
            <div className="case-heading">
              <span className="eyebrow">Active investigation</span>
              <h1>{investigation.name}</h1>
              <code>{shortAddress(investigation.seed)}</code>
            </div>
            <div className={`source-banner ${investigation.data_source}`}>
              <span />
              <div><strong>{investigation.data_source === "live_rpc" ? "Live RPC evidence" : "Synthetic fixture"}</strong><small>{investigation.data_source === "live_rpc" ? "Public Solana data" : "Not on-chain data"}</small></div>
            </div>
            {investigation.limits.notice && <div className="limit-notice">{investigation.limits.notice}</div>}
            <nav className="case-nav" aria-label="Investigation sections">
              <button className={section === "fund-flow" ? "active" : ""} onClick={() => setSection("fund-flow")}><span>⌘</span> Fund flow <b>{investigation.edges.filter((edge) => edge.certainty === "confirmed_fact").length}</b></button>
              <button className={section === "wallets" ? "active" : ""} onClick={() => setSection("wallets")}><span>◫</span> Wallets <b>{investigation.nodes.length}</b></button>
              <button className={section === "relationships" ? "active" : ""} onClick={() => setSection("relationships")}><span>⌁</span> Relationships <b>{investigation.edges.length}</b></button>
              <button className={section === "timeline" ? "active" : ""} onClick={() => setSection("timeline")}><span>◷</span> Timeline <b>{investigation.evidence.length}</b></button>
              <button className={section === "evidence" ? "active" : ""} onClick={() => setSection("evidence")}><span>✓</span> Evidence <b>{investigation.evidence.length}</b></button>
            </nav>
            <section className="candidate-section">
              <div className="section-title"><h3>Consolidation candidates</h3><span>{investigation.exit_candidates.length}</span></div>
              {investigation.exit_candidates.length ? investigation.exit_candidates.slice(0, 3).map((candidate, index) => (
                <button className="candidate-row" key={candidate.address} onClick={() => {
                  const node = investigation.nodes.find((item) => item.address === candidate.address);
                  if (node) setSelection({ kind: "node", value: node });
                }}>
                  <b>0{index + 1}</b><div><code>{shortAddress(candidate.address)}</code><small>{candidate.contributing_wallets} converging wallets</small></div><strong>{Math.round(candidate.evidence_score * 100)}</strong>
                </button>
              )) : <p className="muted">No multi-source convergence observed in this slice.</p>}
            </section>
            <a className="export-link" href={investigation.data_source === "live_rpc" ? exportUrl(investigation.investigation_id) : undefined} aria-disabled={investigation.data_source !== "live_rpc"}>↓ Export evidence snapshot</a>
          </aside>
          <InvestigationWorkspace investigation={investigation} section={section} onSelect={select} />
          <Inspector investigation={investigation} selection={selection} expanding={expanding} onExpand={expand} />
        </main>
      )}
    </div>
  );
}
