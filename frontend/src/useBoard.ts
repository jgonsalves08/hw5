// All board state: loads facts from the backend, polls agent events while a run is going,
// and derives what each agent is doing on a ticket.
import { useCallback, useEffect, useRef, useState } from "react";
import { AGENTS, describe } from "./agents";
import { api } from "./api";
import type { AgentEvent, AgentKey, Approval, Cash, Draft, RunInfo, Ticket } from "./types";
import type { Mood } from "./components/Avatar";

const FAST_POLL_MS = 1200;
const SLOW_POLL_MS = 6000;
const MAX_EVENTS = 4000;

export function useBoard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [activeRun, setActiveRun] = useState<RunInfo | null>(null);
  const [serverBusy, setServerBusy] = useState(false);
  const [offline, setOffline] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; tone: "ok" | "bad" } | null>(null);
  const lastId = useRef<number | undefined>(undefined);

  const say = useCallback((text: string, tone: "ok" | "bad" = "ok") => {
    setToast({ text, tone });
    window.setTimeout(() => setToast((t) => (t?.text === text ? null : t)), 4500);
  }, []);

  const refreshFacts = useCallback(async () => {
    try {
      const [t, c, a, d] = await Promise.all([api.tickets(), api.cash(), api.approvals(), api.drafts()]);
      setTickets(t);
      setCash(c);
      setApprovals(a);
      setDrafts(d);
      setOffline(null);
    } catch (err) {
      setOffline((err as Error).message);
    }
  }, []);

  const pollEvents = useCallback(async () => {
    try {
      const r = await api.events(lastId.current);
      if (r.events.length)
        setEvents((prev) => {
          // two polls can overlap (timer + a button), so only append events we don't have yet
          const seen = prev.length ? prev[prev.length - 1].id : -1;
          const fresh = r.events.filter((e) => e.id > seen);
          return fresh.length ? [...prev, ...fresh].slice(-MAX_EVENTS) : prev;
        });
      lastId.current = r.last_id;
      setServerBusy(r.running);
      setOffline(null);
    } catch (err) {
      setOffline((err as Error).message);
    }
  }, []);

  // first load
  useEffect(() => {
    refreshFacts();
    pollEvents();
  }, [refreshFacts, pollEvents]);

  // fast polling while a run is going, slow polling otherwise (picks up CLI runs too)
  const busy = activeRun?.status === "running" || serverBusy;
  useEffect(() => {
    const id = window.setInterval(async () => {
      await pollEvents();
      if (activeRun?.status === "running") {
        try {
          const run = await api.run(activeRun.run_id);
          if (run.status !== "running") {
            setActiveRun(run);
            await refreshFacts();
            await pollEvents();
            if (run.status === "done") say(`Ticket #${run.ticket_id} resolved — the team is done.`);
            else say(`Ticket #${run.ticket_id} hit a problem: ${run.error ?? "see the play-by-play"}`, "bad");
          }
        } catch (err) {
          // the server restarted (e.g. uvicorn --reload) and no longer knows this run
          if ((err as Error).message.startsWith("No run")) {
            setActiveRun({ ...activeRun, status: "error", error: "the backend restarted mid-run" });
            say(`Run on #${activeRun.ticket_id} was interrupted because the backend restarted. Send the team in again.`, "bad");
            await refreshFacts();
          }
        }
      } else if (!busy) {
        await refreshFacts();
      }
    }, busy ? FAST_POLL_MS : SLOW_POLL_MS);
    return () => window.clearInterval(id);
  }, [activeRun, busy, pollEvents, refreshFacts, say]);

  const startRun = useCallback(
    async (ticketId: number) => {
      try {
        const run = await api.runTicket(ticketId);
        setActiveRun(run);
        say(`The team is on ticket #${ticketId}.`);
        await refreshFacts();
      } catch (err) {
        say((err as Error).message, "bad");
      }
    },
    [refreshFacts, say],
  );

  const approve = useCallback(
    async (a: Approval, name: string) => {
      try {
        await api.approve(a.id, name);
        await refreshFacts();
        await pollEvents();
        say(a.type === "payment" ? `Paid ${a.payee} — approved by ${name}.` : `Purchase order ${a.id} approved by ${name}. Nothing was sent to the vendor.`);
        return true;
      } catch (err) {
        say((err as Error).message, "bad");
        return false;
      }
    },
    [pollEvents, refreshFacts, say],
  );

  const reject = useCallback(
    async (a: Approval, name: string) => {
      try {
        await api.reject(a.id, name, "Rejected on the board");
        await refreshFacts();
        say(`${a.id} rejected.`);
      } catch (err) {
        say((err as Error).message, "bad");
      }
    },
    [refreshFacts, say],
  );

  const reset = useCallback(async () => {
    try {
      await api.reset();
      setActiveRun(null);
      await Promise.all([refreshFacts(), pollEvents()]);
      say("Desk reset to the original data. Fresh start!");
    } catch (err) {
      say((err as Error).message, "bad");
    }
  }, [pollEvents, refreshFacts, say]);

  return { tickets, events, cash, approvals, drafts, activeRun, busy, offline, toast, startRun, approve, reject, reset };
}

// ---------- per-ticket view ----------

export interface AgentState {
  key: AgentKey;
  mood: Mood;
  line: string | null; // what they are saying / doing right now
  summary: string | null; // what they did (from their final report)
  tools: string[];
  handoffs: AgentKey[];
  calls: number;
}

export interface Handoff {
  n: number; // order within the run (1, 2, 3…)
  from: AgentKey;
  to: AgentKey;
  status: "active" | "done" | "error" | "refused";
}

export interface TicketView {
  runId: string | null;
  events: AgentEvent[];
  agents: Record<AgentKey, AgentState>;
  handoffs: Handoff[];
  decision: string | null;
  running: boolean;
}

export function ticketView(all: AgentEvent[], ticketId: number | null, serverBusy = true): TicketView {
  const blank = (key: AgentKey): AgentState => ({ key, mood: "benched", line: null, summary: null, tools: [], handoffs: [], calls: 0 });
  const agents = Object.fromEntries(AGENTS.map((a) => [a.key, blank(a.key)])) as Record<AgentKey, AgentState>;
  // a reset wipes the desk, so runs from before the latest reset no longer apply
  let lastReset = -1;
  for (const e of all) if (e.step === "database_reset") lastReset = e.id;
  const forTicket = all.filter((e) => e.id > lastReset && e.ticket_id === ticketId && e.run_id.startsWith("run-"));
  const runId = forTicket.length ? forTicket[forTicket.length - 1].run_id : null;
  const events = forTicket.filter((e) => e.run_id === runId);

  let decision: string | null = null;
  let running = false;
  const handoffs: Handoff[] = [];
  for (const e of events) {
    // every hand-off becomes its own line on the board
    if (e.agent && e.step === "delegation_start") {
      const to = e.said?.match(/^→ (\w+):/)?.[1] as AgentKey | undefined;
      if (to) handoffs.push({ n: handoffs.length + 1, from: e.agent, to, status: "active" });
    } else if (e.agent && e.step === "delegation_end") {
      const m = e.said?.match(/^← (\w+) \((\w+)\)/);
      const h = m && handoffs.find((x) => x.status === "active" && x.from === e.agent && x.to === m[1]);
      if (h) h.status = m[2] === "done" ? "done" : "error";
    } else if (e.agent && e.step === "delegation_refused") {
      const to = e.said?.match(/^✕ (\w+):/)?.[1] as AgentKey | undefined;
      if (to) handoffs.push({ n: handoffs.length + 1, from: e.agent, to, status: "refused" });
    }
    if (e.step === "ticket_start") running = true;
    if (e.step === "ticket_end" || e.step === "ticket_marked_resolved") running = false;
    if (!e.agent) continue;
    const s = agents[e.agent];
    if (!s) continue;
    if (e.step === "run_start") {
      s.mood = "working";
      s.calls += 1;
    } else if (e.step === "run_end") {
      s.mood = "done";
      s.summary = e.said;
      if (e.agent === "boss") decision = e.said;
    } else if (e.step === "run_error") {
      s.mood = "error";
    } else if (e.step === "tool_call") {
      for (const t of e.tools) if (!s.tools.includes(t)) s.tools.push(t);
    } else if (e.step === "delegation_start") {
      const to = e.said?.match(/^→ (\w+):/)?.[1] as AgentKey | undefined;
      if (to && !s.handoffs.includes(to)) s.handoffs.push(to);
    }
    const line = describe(e);
    if (line) s.line = line;
  }
  // a run the server is no longer working on was interrupted (e.g. the backend restarted)
  if (running && !serverBusy) running = false;
  // any agent still "working" after the ticket ended didn't finish cleanly
  if (!running) {
    for (const s of Object.values(agents)) if (s.mood === "working") {
      s.mood = "error";
      s.line = "Interrupted before finishing — send the team in again.";
    }
    for (const h of handoffs) if (h.status === "active") h.status = "error";
  }
  return { runId, events, agents, handoffs, decision, running };
}
