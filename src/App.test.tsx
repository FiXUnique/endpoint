import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./components/GraphCanvas", () => ({
  GraphCanvas: () => <div aria-label="Interactive fund-flow graph" />,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Endpoint app", () => {
  it("labels the demo as synthetic and never presents it as live evidence", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        investigation_id: "demo",
        name: "Synthetic demonstration",
        chain: "solana",
        seed: "Seed111111111111111111111111111111111111",
        data_source: "synthetic_demo",
        created_at: new Date().toISOString(),
        nodes: [], edges: [], evidence: [], exit_candidates: [],
        limits: { requested_signatures: 0, returned_signatures: 0, truncated: false, notice: "Synthetic fixture" },
        methodology_version: "0.1.0",
      }),
    }));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /open synthetic demo/i }));
    await waitFor(() => expect(screen.getAllByText("Synthetic fixture")).toHaveLength(2));
    expect(screen.getByText("Not on-chain data")).toBeInTheDocument();
  });

  it("opens functional wallet, relationship, timeline, and evidence sections", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        investigation_id: "demo",
        name: "Synthetic demonstration",
        chain: "solana",
        seed: "Seed111111111111111111111111111111111111",
        data_source: "synthetic_demo",
        created_at: new Date().toISOString(),
        nodes: [{
          id: "wallet-a", address: "Wallet1111111111111111111111111111111111", kind: "wallet",
          label: null, seed: false, incoming_count: 1, outgoing_count: 0, observed_assets: ["SOL"],
        }],
        edges: [{
          id: "edge-a", source: "Seed111111111111111111111111111111111111",
          target: "Wallet1111111111111111111111111111111111", relationship: "observed_transfer",
          certainty: "confirmed_fact", evidence_score: 1, label: "1 SOL", asset: "SOL",
          amount: "1", transfer_count: 1, signals: [], evidence_ids: ["ev-a"],
        }],
        evidence: [{
          id: "ev-a", chain: "solana", signature: "Signature111111111111111111111111111111111111111111111111",
          slot: 42, timestamp: new Date().toISOString(), source: "Seed111111111111111111111111111111111111",
          target: "Wallet1111111111111111111111111111111111", asset: "SOL", amount: "1",
          instruction_path: "outer:0", rpc_url: null, retrieved_at: new Date().toISOString(),
        }],
        exit_candidates: [],
        limits: { requested_signatures: 0, returned_signatures: 0, truncated: false, notice: "Synthetic fixture" },
        methodology_version: "0.1.0",
      }),
    }));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /open synthetic demo/i }));
    await screen.findByLabelText("Interactive fund-flow graph");

    fireEvent.click(screen.getByRole("button", { name: /wallets 1/i }));
    expect(screen.getByLabelText("Observed wallets")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /relationships 1/i }));
    expect(screen.getByLabelText("Relationships")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /timeline 1/i }));
    expect(screen.getByLabelText("Transaction timeline")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /evidence 1/i }));
    expect(screen.getByLabelText("Evidence ledger")).toBeInTheDocument();
  });

  it("offers a smaller retry when the RPC reports a retryable failure", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ detail: "RPC remained rate-limited", code: "rpc_rate_limited", retryable: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          investigation_id: "live", name: "Live trace", chain: "solana",
          seed: "Seed111111111111111111111111111111111111", data_source: "live_rpc",
          created_at: new Date().toISOString(), nodes: [], edges: [], evidence: [], exit_candidates: [],
          limits: { requested_signatures: 10, returned_signatures: 0, truncated: false, notice: null },
          methodology_version: "0.1.0",
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.change(screen.getByLabelText("Solana wallet or mint address"), {
      target: { value: "Seed111111111111111111111111111111111111" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Trace funds" }));
    await screen.findByText("RPC remained rate-limited");
    fireEvent.click(screen.getByRole("button", { name: "Retry with 10 txs" }));
    await screen.findByText("Live trace");

    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toMatchObject({
      signature_limit: 10,
    });
    expect(screen.getByText("No supported transfers in this transaction slice")).toBeInTheDocument();
  });
});
