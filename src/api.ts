import type { Investigation } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function traceAddress(address: string, signatureLimit: number): Promise<Investigation> {
  return request("/api/v1/investigations/trace", {
    method: "POST",
    body: JSON.stringify({ address, signature_limit: signatureLimit }),
  });
}

export function expandAddress(
  investigationId: string,
  address: string,
  signatureLimit = 15,
): Promise<Investigation> {
  return request("/api/v1/investigations/expand", {
    method: "POST",
    body: JSON.stringify({
      investigation_id: investigationId,
      address,
      signature_limit: signatureLimit,
    }),
  });
}

export function loadDemo(): Promise<Investigation> {
  return request("/api/v1/demo");
}

export function exportUrl(investigationId: string): string {
  return `${API_URL}/api/v1/investigations/${investigationId}/export`;
}
