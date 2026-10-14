// Shapes returned by the FastAPI backend (backend/main.py).

export type AgentKey = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface Ticket {
  id: number;
  type: "customer_order" | "rent_notice" | "price_override" | string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  notes: string | null;
  status: string;
  state: "open" | "resolved";
}

export interface AgentEvent {
  id: number;
  run_id: string;
  seq: number;
  ts: string;
  ticket_id: number | null;
  agent: AgentKey | null;
  depth: number | null;
  parent_agent: AgentKey | null;
  step: string;
  said: string | null;
  tools: string[];
  detail: unknown;
}

export interface EventsResponse {
  events: AgentEvent[];
  last_id: number;
  running: boolean;
}

export interface Cash {
  name: string;
  balance: number;
  as_of: string;
  pending_approval_payments: number;
  available_after_pending: number;
}

export interface Approval {
  id: string;
  type: "payment" | "purchase_order";
  status: "pending" | "paid" | "approved" | "rejected";
  ticket_id: number | null;
  reason: string;
  prepared_by: AgentKey;
  prepared_at: string;
  approved_by?: string;
  rejected_by?: string;
  // payment
  kind?: "invoice" | "rent";
  ref_id?: number;
  payee?: string;
  amount?: number;
  due_date?: string;
  days_until_due?: number;
  description?: string;
  balance_after_if_approved?: number;
  // purchase order
  vendor?: string;
  sku?: string;
  size?: string;
  qty?: number;
  estimated_cost?: number;
  eta_if_approved_today?: string;
  will_ship?: boolean;
}

export interface Draft {
  id: string;
  ticket_id: number;
  to: string;
  subject: string;
  body: string;
  drafted_by: AgentKey;
  drafted_at: string;
  status: string;
}

export interface RunInfo {
  run_id: string;
  ticket_id: number;
  status: "running" | "done" | "error";
  error?: string;
}
