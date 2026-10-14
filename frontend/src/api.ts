// Thin client for the Problem 7 routes. The backend runs at http://localhost:8000.
import type { Approval, Cash, Draft, EventsResponse, RunInfo, Ticket } from "./types";

export const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(`Can't reach the backend at ${API_BASE}. Start it from backend/ with: uvicorn main:app --reload --port 8000`);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    throw new ApiError(detail);
  }
  return body as T;
}

export const api = {
  tickets: () => request<{ tickets: Ticket[] }>("/api/tickets").then((r) => r.tickets),
  runTicket: (id: number) => request<RunInfo>(`/api/tickets/${id}/run`, { method: "POST" }),
  run: (runId: string) => request<RunInfo>(`/api/runs/${runId}`),
  events: (after?: number, limit = 1000) =>
    request<EventsResponse>(`/api/events?limit=${limit}${after !== undefined ? `&after=${after}` : ""}`),
  approvals: () => request<{ approvals: Approval[] }>("/api/approvals?status=all").then((r) => r.approvals),
  approve: (id: string, approvedBy: string) =>
    request<Record<string, unknown>>(`/api/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  reject: (id: string, rejectedBy: string, reason: string) =>
    request<Record<string, unknown>>(`/api/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejected_by: rejectedBy, reason }),
    }),
  cash: () => request<Cash>("/api/cash"),
  drafts: () => request<{ drafts: Draft[] }>("/api/drafts").then((r) => r.drafts),
  reset: () => request<Record<string, unknown>>("/api/reset", { method: "POST" }),
};
