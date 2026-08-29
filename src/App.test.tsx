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
        exit_candidates: [{
          address: "Wallet1111111111111111111111111111111111",
          evidence_score: 0.92,
          label: "likely observed endpoint",
          explanation: "The meaningful observed trail stops here.",
          contributing_wallets: 1,
          evidence_ids: ["ev-a"],
          direct_from_seed: true,
          terminal_in_observed_graph: true,
          hop_distance: 1,
          incoming_transfer_count: 1,
          outgoing_transfer_count: 0,
          received_assets: [{ asset: "SOL", amount: "1" }],
        }],
        limits: { requested_signatures: 0, returned_signatures: 0, truncated: false, notice: "Synthetic fixture" },
        methodology_version: "0.1.0",
      }),
    }));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /open synthetic demo/i }));
    await screen.findByLabelText("Interactive fund-flow graph");
    expect(screen.getByLabelText("Likely endpoint")).toHaveTextContent("Money arrived");
    expect(screen.getByLabelText("Likely endpoint")).toHaveTextContent("1 SOL");
    expect(screen.getByLabelText("Likely endpoint")).toHaveTextContent("The money trail stops at this wallet");

    fireEvent.click(screen.getByRole("button", { name: /wallets found 1/i }));
    expect(screen.getByLabelText("Wallets found")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /possible links 0/i }));
    expect(screen.getByText(/No extra wallet links were suggested/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /transactions 1/i }));
    expect(screen.getByLabelText("Transactions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /raw proof 1/i }));
    expect(screen.getByLabelText("Raw proof")).toBeInTheDocument();
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
    fireEvent.change(screen.getByLabelText("Blockchain network"), {
      target: { value: "solana" },
    });
    fireEvent.change(screen.getByLabelText("Wallet address"), {
      target: { value: "Seed111111111111111111111111111111111111" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Trace funds" }));
    await screen.findByText("RPC remained rate-limited");
    fireEvent.click(screen.getByRole("button", { name: "Retry with 10 txs" }));
    await screen.findByText("Live trace");

    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toMatchObject({
      chain: "solana",
      signature_limit: 10,
    });
    expect(screen.getByText("No money trail was found in this scan")).toBeInTheDocument();
  });

  it("accepts a 0x address and sends the selected EVM network", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        investigation_id: "evm-empty",
        name: "Ethereum trace 0xec14…3577",
        chain: "ethereum",
        seed: "0xec149f3cdb488e4001fba55b9114f89139fd3577",
        data_source: "live_indexer",
        created_at: new Date().toISOString(),
        nodes: [{
          id: "0xec149f3cdb488e4001fba55b9114f89139fd3577",
          address: "0xec149f3cdb488e4001fba55b9114f89139fd3577",
          kind: "wallet", label: null, seed: true, incoming_count: 0,
          outgoing_count: 0, observed_assets: [],
        }],
        edges: [], evidence: [], exit_candidates: [],
        limits: {
          requested_signatures: 25, returned_signatures: 0,
          processed_transactions: 0, failed_transactions: 0, truncated: false,
          notice: "No indexed transactions were found for this address on Ethereum.",
        },
        methodology_version: "0.2.0",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.change(screen.getByLabelText("Wallet address"), {
      target: { value: "0xec149f3cdb488e4001fba55b9114f89139fd3577" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Trace funds" }));

    await screen.findByText("No money trail was found in this scan");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toMatchObject({
      chain: "ethereum",
      address: "0xec149f3cdb488e4001fba55b9114f89139fd3577",
    });
    expect(screen.getAllByText("Ethereum mainnet").length).toBeGreaterThan(0);
    expect(screen.getByText(/There is no stopping wallet to show yet/)).toBeInTheDocument();
  });

  it("offers working BNB and Robinhood network choices", () => {
    render(<App />);
    const network = screen.getByLabelText("Blockchain network");
    expect(network).toHaveTextContent("BNB Smart Chain");
    expect(network).toHaveTextContent("Robinhood Chain");
  });
});
