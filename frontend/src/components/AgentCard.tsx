import { AGENT_BY_KEY, toolLabel } from "../agents";
import type { AgentState } from "../useBoard";
import Avatar from "./Avatar";

const STATUS: Record<AgentState["mood"], string> = {
  benched: "Not called",
  idle: "Ready",
  working: "Working",
  done: "Done",
  error: "Stuck",
};

export default function AgentCard({
  state,
  hasRun,
  running = false,
  featured = false,
}: {
  state: AgentState;
  hasRun: boolean;
  running?: boolean;
  featured?: boolean;
}) {
  const meta = AGENT_BY_KEY[state.key];
  const mood = (!hasRun || running) && state.mood === "benched" ? "idle" : state.mood;
  const text = mood === "done" ? state.summary : state.line;

  return (
    <article
      data-agent={state.key}
      className={`agent-card mood-${mood} ${featured ? "featured" : ""}`}
      style={{ ["--accent" as string]: meta.accent }}
    >
      <div className="agent-pop">
        <Avatar role={state.key} mood={mood} size={featured ? 118 : 96} />
      </div>
      <span className={`pill-black agent-status status-${mood}`}>
        {mood === "working" && <span className="pulse-dot" />}
        {STATUS[mood]}
      </span>
      <h3>{meta.name}</h3>
      <p className="agent-role">{meta.role}</p>

      <div className={`bubble ${text ? "" : "bubble-empty"}`}>
        {mood === "done" && <span className="bubble-label">What I did</span>}
        <p>{text ?? (running ? "Standing by in case the team needs me…" : hasRun ? "Not needed on this ticket." : "Waiting for a ticket.")}</p>
        {mood === "working" && (
          <span className="typing" aria-label="thinking">
            <i />
            <i />
            <i />
          </span>
        )}
      </div>

      {state.tools.length > 0 && (
        <div className="tool-chips">
          {state.tools.map((t) => (
            <span key={t} className="tool-chip" title={toolLabel(t)}>
              {t}
            </span>
          ))}
        </div>
      )}
      {state.handoffs.length > 0 && (
        <p className="handoffs">
          Handed off to {state.handoffs.map((k) => AGENT_BY_KEY[k]?.name ?? k).join(", ")}
        </p>
      )}
    </article>
  );
}
