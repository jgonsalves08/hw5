// The five agents, how each one looks, and plain-English labels for their tools.
import type { AgentEvent, AgentKey } from "./types";

export interface AgentMeta {
  key: AgentKey;
  name: string;
  role: string;
  color: string; // body color of the character
  accent: string; // tint used for chips and the activity feed
}

export const AGENTS: AgentMeta[] = [
  { key: "boss", name: "Boss", role: "Routes tickets · makes the call", color: "#2f3a33", accent: "#e8c35a" },
  { key: "inventory", name: "Inventory", role: "Stock, shortfalls, restocks", color: "#e8823a", accent: "#e8823a" },
  { key: "accounting", name: "Accounting", role: "Cash, invoices, margins", color: "#3f8f4a", accent: "#3f8f4a" },
  { key: "facilities", name: "Facilities", role: "Leases & rent", color: "#d9a92c", accent: "#c9971d" },
  { key: "customer_service", name: "Customer Service", role: "Drafts customer replies", color: "#e0677a", accent: "#e0677a" },
];

export const AGENT_BY_KEY = Object.fromEntries(AGENTS.map((a) => [a.key, a])) as Record<AgentKey, AgentMeta>;

const TOOL_LABELS: Record<string, string> = {
  get_ticket: "Reading the ticket",
  list_tickets: "Scanning the ticket queue",
  get_desk_today: "Checking today's desk date",
  check_inventory: "Counting stock on the shelves",
  check_price: "Checking cost and list price",
  check_overdue: "Checking the due date",
  list_vendors: "Looking up vendors and lead times",
  list_invoices: "Reviewing vendor invoices",
  list_leases: "Pulling up the lease",
  list_payments: "Checking past payments",
  list_obligations: "Lining up everything we owe",
  get_cash_balance: "Checking the cash balance",
  list_approvals: "Looking at the approval queue",
  list_drafts: "Looking at saved drafts",
  prepare_payment: "Queuing a payment for your approval",
  prepare_purchase_order: "Queuing a purchase order for your approval",
  draft_customer_message: "Writing a draft (not sent)",
  update_ticket_status: "Updating the ticket status",
  ask_agent: "Handing off to a teammate",
};

export const toolLabel = (tool: string) => TOOL_LABELS[tool] ?? tool.replace(/_/g, " ");

const name = (key: string | null | undefined) => (key && AGENT_BY_KEY[key as AgentKey]?.name) || key || "someone";

/** One readable line for the speech bubble / feed. Returns null for steps not worth showing. */
export function describe(e: AgentEvent): string | null {
  const d = (e.detail ?? {}) as Record<string, unknown>;
  switch (e.step) {
    case "run_start":
      return e.depth === 0 ? "Reading the ticket…" : `Got a task from ${name(e.parent_agent)}`;
    case "tool_call":
      return `${toolLabel(e.tools[0] ?? "")}…`;
    case "tool_refused":
      return `Blocked from using ${e.tools[0]}`;
    case "model_response":
      return e.said || null;
    case "delegation_start": {
      const to = e.said?.match(/^→ (\w+):/)?.[1];
      return `Asking ${name(to)} for help`;
    }
    case "delegation_end": {
      const to = e.said?.match(/^← (\w+)/)?.[1];
      return `${name(to)} reported back`;
    }
    case "delegation_refused":
      return "Hand-off refused by a guardrail (loop or budget limit)";
    case "run_end":
      return e.said;
    case "run_error":
      return `Hit a problem: ${e.said ?? "error"}`;
    case "ticket_marked_resolved":
      return "Ticket marked resolved";
    case "human_decision":
      return e.said;
    default:
      return d && typeof d === "object" && "error" in d ? String(d.error) : null;
  }
}

export const money = (n: number | undefined | null) =>
  (n ?? 0).toLocaleString("en-US", { style: "currency", currency: "USD" });
