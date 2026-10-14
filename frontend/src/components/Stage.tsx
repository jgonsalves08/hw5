import { useEffect, useMemo, useRef, useState } from "react";
import { AGENT_BY_KEY, describe } from "../agents";
import type { AgentKey, Ticket } from "../types";
import type { TicketView } from "../useBoard";
import AgentCard from "./AgentCard";
import HandoffLines from "./HandoffLines";
import Avatar from "./Avatar";

const SPECIALISTS: AgentKey[] = ["inventory", "accounting", "facilities", "customer_service"];

export default function Stage({
  ticket,
  view,
  isRunning,
  busy,
  onRun,
  pendingForTicket,
  onGoApprove,
}: {
  ticket: Ticket | null;
  view: TicketView;
  isRunning: boolean;
  busy: boolean;
  onRun: () => void;
  pendingForTicket: number;
  onGoApprove: () => void;
}) {
  const hasRun = view.runId !== null;
  const resolved = ticket?.state === "resolved";
  const gridRef = useRef<HTMLDivElement>(null);
  const [extraSpace, setExtraSpace] = useState(0);

  // "Boss → Accounting ×2" style tally of every hand-off in this run
  const tally = useMemo(() => {
    const counts = new Map<string, { from: AgentKey; to: AgentKey; n: number; refused: number }>();
    for (const h of view.handoffs) {
      const k = `${h.from}>${h.to}`;
      const row = counts.get(k) ?? { from: h.from, to: h.to, n: 0, refused: 0 };
      if (h.status === "refused") row.refused += 1;
      else row.n += 1;
      counts.set(k, row);
    }
    return [...counts.values()];
  }, [view.handoffs]);

  return (
    <section className="panel panel-dark stage">
      <div className="stage-top">
        <span className="eyebrow">
          <SparkIcon /> Agent team
        </span>
        {ticket && <span className="pill-glass">#{ticket.id} · {ticket.requester}</span>}
      </div>

      <h1 className="stage-title">Agent Team</h1>
      {ticket ? (
        <div className="working-on">
          <span className="working-label">Working on</span>
          <strong>
            #{ticket.id} · {ticket.subject}
          </strong>
          {ticket.notes && <span className="working-notes">{ticket.notes}</span>}
        </div>
      ) : (
        <p className="stage-sub">Pick a ticket on the right to get started.</p>
      )}

      {/* the main action sits right under the ticket so it's the first thing you see */}
      <div className="cta-wrap" id="run-team">
        <button
          className={`cta-white ${ticket && !isRunning && !busy && !resolved ? "cta-ready" : ""}`}
          disabled={!ticket || isRunning || busy || resolved}
          onClick={onRun}
        >
          {isRunning ? (
            <>
              <span className="spinner dark" /> The team is working on #{ticket?.id}…
            </>
          ) : resolved ? (
            "✓ Resolved — reset the desk to run it again"
          ) : busy ? (
            "Another run is in progress…"
          ) : ticket ? (
            <>
              <PlayIcon /> Send the team in on #{ticket.id}
            </>
          ) : (
            "Pick a ticket first"
          )}
        </button>
        <p className="cta-hint">
          {isRunning
            ? "Watch each agent below. The Boss reads the ticket and calls in teammates (about a minute)."
            : resolved
              ? "This ticket is done. Pick another ticket on the right, or reset the desk to start over."
              : busy
                ? "The team is busy with another ticket. Click that ticket on the right to watch, or wait for it to finish."
                : ticket
                ? "Click the button to start. The Boss reads the ticket and calls in the right teammates."
                : "Tickets are listed on the right."}
        </p>
      </div>

      {pendingForTicket > 0 && !isRunning && (
        <button className="your-turn" onClick={onGoApprove}>
          <span className="your-turn-badge">Your turn</span>
          <span>
            The team queued {pendingForTicket === 1 ? "a request" : `${pendingForTicket} requests`} for #{ticket?.id} that
            needs your approval.
          </span>
          <strong>Approve it →</strong>
        </button>
      )}

      <div className="agent-grid" ref={gridRef} style={{ paddingBottom: extraSpace }}>
        <AgentCard state={view.agents.boss} hasRun={hasRun} running={isRunning} featured />
        <div className="specialists">
          {SPECIALISTS.map((k) => (
            <AgentCard key={k} state={view.agents[k]} hasRun={hasRun} running={isRunning} />
          ))}
        </div>
        <HandoffLines handoffs={view.handoffs} container={gridRef} onExtraSpace={setExtraSpace} />
      </div>

      {tally.length > 0 && (
        <div className="handoff-tally">
          <span className="handoff-tally-title">
            Hand-offs <strong>{view.handoffs.length}</strong>
          </span>
          {tally.map((t) => (
            <span key={`${t.from}>${t.to}`} className="handoff-chip" style={{ ["--accent" as string]: AGENT_BY_KEY[t.from].accent }}>
              <i />
              {AGENT_BY_KEY[t.from].name} → {AGENT_BY_KEY[t.to].name}
              {t.n > 0 && <b>×{t.n}</b>}
              {t.refused > 0 && <em>{t.refused} refused</em>}
            </span>
          ))}
        </div>
      )}

      {view.decision && !isRunning && (
        <div className="decision-card">
          <span className="pill-black decision-pill">Boss's call</span>
          <p>{view.decision}</p>
        </div>
      )}

      <Feed view={view} />
    </section>
  );
}

function Feed({ view }: { view: TicketView }) {
  const ref = useRef<HTMLOListElement>(null);
  const rows = view.events
    .map((e) => ({ e, text: describe(e) }))
    .filter((r) => r.text && r.e.agent && r.e.step !== "run_start");

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [rows.length]);

  return (
    <div className="feed">
      <div className="feed-head">
        <h4>Play-by-play</h4>
        <span>{rows.length} steps</span>
      </div>
      {rows.length === 0 ? (
        <p className="feed-empty">Nothing yet. Steps appear here as each agent thinks, calls a tool, or hands off.</p>
      ) : (
        <ol ref={ref}>
          {rows.map(({ e, text }) => {
            const meta = AGENT_BY_KEY[e.agent as AgentKey];
            return (
              <li key={e.id} style={{ ["--accent" as string]: meta?.accent ?? "#999", ["--indent" as string]: e.depth ?? 0 }}>
                <span className="feed-avatar">
                  <Avatar role={e.agent as AgentKey} mood={e.step === "run_end" ? "done" : "idle"} size={26} />
                </span>
                <div>
                  <span className="feed-who">
                    {meta?.name}
                    <time>{new Date(e.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time>
                  </span>
                  <span className="feed-text">{text}</span>
                  {e.step === "tool_call" && <code className="tool-chip small">{e.tools[0]}</code>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

const PlayIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5Z" />
  </svg>
);

const SparkIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M12 2l2.2 6.3L20 10l-5.8 1.7L12 18l-2.2-6.3L4 10l5.8-1.7z" />
  </svg>
);
