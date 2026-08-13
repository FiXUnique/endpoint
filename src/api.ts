import type { Investigation, SupportedChain } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? "" : "http://localhost:8000");

export class ApiError extends Error {
  code: string | null;
  retryable: boolean;

  constructor(message: string, code: string | null = null, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.retryable = retryable;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
      code?: string;
      retryable?: boolean;
    } | null;
    throw new ApiError(
      payload?.detail ?? `Request failed (${response.status})`,
      payload?.code ?? null,
      payload?.retryable ?? response.status >= 500,
    );
  }
  return response.json() as Promise<T>;
}

export function traceAddress(
  chain: SupportedChain,
  address: string,
  signatureLimit: number,
): Promise<Investigation> {
  return request("/api/v1/investigations/trace", {
    method: "POST",
    body: JSON.stringify({ chain, address, signature_limit: signatureLimit }),
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
