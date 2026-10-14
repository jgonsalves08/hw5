import { useEffect, useMemo, useState } from "react";
import { API_BASE } from "./api";
import CashPanel from "./components/CashPanel";
import GuideBar, { type Step } from "./components/GuideBar";
import Stage from "./components/Stage";
import TicketsPanel from "./components/TicketsPanel";
import { ticketView, useBoard } from "./useBoard";
import "./App.css";

export default function App() {
  const board = useBoard();
  // ?ticket=101 opens the board on that ticket (handy for links and screenshots)
  const [picked, setPicked] = useState<number | null>(() => Number(new URLSearchParams(location.search).get("ticket")) || null);
  const [confirmReset, setConfirmReset] = useState(false);

  // pick the first open ticket once tickets load, then keep whatever the user picks
  useEffect(() => {
    if (picked === null && board.tickets.length)
      setPicked(board.tickets.find((t) => t.state === "open")?.id ?? board.tickets[0].id);
  }, [picked, board.tickets]);
  const selected = picked;
  const ticket = board.tickets.find((t) => t.id === selected) ?? null;
  const view = useMemo(() => ticketView(board.events, selected, board.busy), [board.events, selected, board.busy]);

  const runningTicket = board.activeRun?.status === "running" ? board.activeRun.ticket_id : null;
  const pendingByTicket = useMemo(() => {
    const out: Record<number, number> = {};
    for (const a of board.approvals) if (a.status === "pending" && a.ticket_id) out[a.ticket_id] = (out[a.ticket_id] ?? 0) + 1;
    return out;
  }, [board.approvals]);

  const isRunning = runningTicket === selected || view.running;
  const pendingTotal = Object.values(pendingByTicket).reduce((a, b) => a + b, 0);
  const step: Step = !ticket ? 1 : pendingTotal > 0 && !isRunning ? 3 : ticket.state === "open" || isRunning ? 2 : 1;

  function goTo(s: Step) {
    if (s === 3) return goApprove();
    const target = document.getElementById(s === 1 ? "tickets" : "run-team");
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // jump to the approval box; put the cursor in the name field if it's empty
  function goApprove() {
    document.getElementById("approvals")?.scrollIntoView({ behavior: "smooth", block: "start" });
    const input = document.getElementById("approver-name") as HTMLInputElement | null;
    window.setTimeout(() => {
      if (input && !input.value.trim()) input.focus({ preventScroll: true });
      else (document.querySelector(".approval .btn-black") as HTMLButtonElement | null)?.focus({ preventScroll: true });
    }, 450);
  }

  async function onReset() {
    if (!confirmReset) {
      setConfirmReset(true);
      window.setTimeout(() => setConfirmReset(false), 4000);
      return;
    }
    setConfirmReset(false);
    await board.reset();
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">CC</span>
          <div>
            <strong>Campus Customs</strong>
            <span className={board.offline ? "status-off" : "status-on"}>
              {board.offline ? "Backend offline" : `Desk open · ${board.cash?.as_of ?? "…"}`}
            </span>
          </div>
        </div>
        <div className="top-actions">
          <span className="pill-outline">5 agents · gpt-6-luna</span>
          <button className="btn-black-lg" onClick={onReset} disabled={board.busy}>
            {confirmReset ? "Tap again to reset the desk" : "Reset desk"}
          </button>
        </div>
      </header>

      {board.offline && (
        <div className="offline-banner">
          {board.offline}
          <small>The board is looking for the API at {API_BASE}.</small>
        </div>
      )}

      <GuideBar current={step} running={isRunning} pending={pendingTotal} onStep={goTo} />

      <main className="canvas">
        <Stage
          ticket={ticket}
          view={view}
          isRunning={isRunning}
          busy={board.busy && runningTicket !== selected}
          onRun={() => selected !== null && board.startRun(selected)}
          pendingForTicket={selected !== null ? pendingByTicket[selected] ?? 0 : 0}
          onGoApprove={goApprove}
        />
        <aside className="side">
          <TicketsPanel
            tickets={board.tickets}
            selected={selected}
            onSelect={setPicked}
            pendingByTicket={pendingByTicket}
            runningTicket={runningTicket}
          />
          <CashPanel
            cash={board.cash}
            approvals={board.approvals}
            drafts={board.drafts}
            selectedTicket={selected}
            teamBusy={board.busy}
            onApprove={board.approve}
            onReject={board.reject}
          />
        </aside>
      </main>

      {board.toast && <div className={`toast toast-${board.toast.tone}`}>{board.toast.text}</div>}
    </div>
  );
}
