import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./components/GraphCanvas", () => ({
  GraphCanvas: () => <div aria-label="Interactive fund-flow graph" />,
}));

afterEach(() => vi.restoreAllMocks());

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
});
