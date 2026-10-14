import { useEffect, useRef, useState } from "react";
import { AGENT_BY_KEY, money } from "../agents";
import type { Approval, Cash, Draft } from "../types";
import Avatar from "./Avatar";

/** Rolls a number toward its new value so a payment visibly drains the balance.
 *  The first real value (page load) and reduced-motion users get the number immediately. */
function useRolling(value: number | null, ms = 1100) {
  const [shown, setShown] = useState(value ?? 0);
  const from = useRef<number | null>(value);
  useEffect(() => {
    if (value === null) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (from.current === null || reduce) {
      from.current = value;
      setShown(value);
      return;
    }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(a + (value - a) * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
      else from.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return shown;
}

export default function CashPanel({
  cash,
  approvals,
  drafts,
  selectedTicket,
  teamBusy,
  onApprove,
  onReject,
}: {
  cash: Cash | null;
  approvals: Approval[];
  drafts: Draft[];
  selectedTicket: number | null;
  teamBusy: boolean;
  onApprove: (a: Approval, name: string) => Promise<boolean>;
  onReject: (a: Approval, name: string) => Promise<void>;
}) {
  const [name, setName] = useState(() => localStorage.getItem("cc-approver") ?? "");
  useEffect(() => localStorage.setItem("cc-approver", name), [name]);

  const pending = approvals.filter((a) => a.status === "pending");
  const decided = approvals.filter((a) => a.status !== "pending").slice(-4).reverse();
  const ticketDrafts = drafts.filter((d) => selectedTicket === null || d.ticket_id === selectedTicket);

  return (
    <section className="panel panel-light cash-panel">
      <CashCard cash={cash} />

      <div className="section-head" id="approvals">
        <h3>Needs your OK</h3>
        {pending.length > 0 && <span className="pill-black">{pending.length}</span>}
      </div>
      <p className="section-note">Agents can only queue these. Nothing is paid or ordered until a person approves.</p>

      {pending.length > 0 && teamBusy && (
        <p className="busy-note">The team is working on a ticket. Approvals unlock as soon as the run finishes, so cash can't change mid-run.</p>
      )}

      {pending.length > 0 && (
        <ol className="how-to">
          <li className={name.trim() ? "done" : "now"}>
            <span>1</span> Type your name in the box below
          </li>
          <li className={name.trim() ? "now" : ""}>
            <span>2</span> Click <strong>Approve</strong> on a request, then click again to confirm
          </li>
        </ol>
      )}

      <label className={`approver ${pending.length > 0 && !name.trim() ? "needs-attention" : ""}`}>
        <span>Approving as</span>
        <input
          id="approver-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Type your name here"
          maxLength={60}
        />
      </label>

      {pending.length === 0 ? (
        <div className="empty-card">
          <span className="empty-check">✓</span>
          <p>Nothing waiting. When an agent queues a payment or purchase order, it lands here.</p>
        </div>
      ) : (
        <div className="approval-list">
          {pending.map((a) => (
            <ApprovalCard key={a.id} a={a} name={name.trim()} highlight={a.ticket_id === selectedTicket}
              cash={cash} teamBusy={teamBusy} onApprove={onApprove} onReject={onReject} />
          ))}
        </div>
      )}

      {decided.length > 0 && (
        <ul className="history">
          {decided.map((a) => (
            <li key={a.id} className={`history-${a.status}`}>
              <span>{a.status === "rejected" ? "✕" : "✓"}</span>
              {a.id} · {a.type === "payment" ? `${money(a.amount)} to ${a.payee}` : `${a.qty} × ${a.sku} ${a.size}`}
              <em>
                {a.status} by {a.approved_by ?? a.rejected_by}
              </em>
            </li>
          ))}
        </ul>
      )}

      <div className="section-head">
        <h3>Drafts</h3>
        <span className="pill-soft">not sent</span>
      </div>
      {ticketDrafts.length === 0 ? (
        <p className="section-note">{selectedTicket ? `No drafts for #${selectedTicket} yet.` : "No drafts yet."}</p>
      ) : (
        ticketDrafts.map((d) => (
          <details key={d.id} className="draft">
            <summary>
              <span className="envelope">✉</span>
              <span>
                <strong>{d.subject}</strong>
                <small>To {d.to} · #{d.ticket_id} · by {AGENT_BY_KEY[d.drafted_by]?.name ?? d.drafted_by}</small>
              </span>
            </summary>
            <p>{d.body}</p>
          </details>
        ))
      )}
    </section>
  );
}

function CashCard({ cash }: { cash: Cash | null }) {
  const balance = cash?.balance ?? 0;
  const shown = useRolling(cash ? balance : null);
  const prev = useRef<number | null>(null);
  const [drop, setDrop] = useState<{ amount: number; key: number } | null>(null);

  useEffect(() => {
    if (cash === null) return;
    let timer = 0;
    if (prev.current !== null && balance < prev.current) {
      setDrop({ amount: prev.current - balance, key: Date.now() });
      timer = window.setTimeout(() => setDrop(null), 2800);
    }
    prev.current = balance;
    return () => window.clearTimeout(timer);
  }, [balance, cash]);

  const pending = cash?.pending_approval_payments ?? 0;
  const pct = balance > 0 ? Math.min(100, (pending / balance) * 100) : 0;

  return (
    <div className={`cash-card ${drop ? "just-dropped" : ""}`} key={drop?.key}>
      <div className="cash-top">
        <span className="cash-label">Checking Account</span>
        <span className="pill-soft">as of {cash?.as_of ?? "—"}</span>
      </div>
      <div className="cash-amount">
        {money(shown)}
        {drop && (
          <span className="cash-drop" key={drop.key}>
            −{money(drop.amount)}
          </span>
        )}
      </div>
      <div className="meter" title="Share of checking already promised to queued payments">
        <span style={{ width: `${pct}%` }} />
      </div>
      <div className="cash-row">
        <span>
          Queued <strong>{money(pending)}</strong>
        </span>
        <span>
          Left after <strong className={cash && cash.available_after_pending < 500 ? "tight" : ""}>{money(cash?.available_after_pending)}</strong>
        </span>
      </div>
    </div>
  );
}

function ApprovalCard({
  a,
  name,
  highlight,
  cash,
  teamBusy,
  onApprove,
  onReject,
}: {
  a: Approval;
  name: string;
  highlight: boolean;
  cash: Cash | null;
  teamBusy: boolean;
  onApprove: (a: Approval, name: string) => Promise<boolean>;
  onReject: (a: Approval, name: string) => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const isPay = a.type === "payment";
  const amount = isPay ? a.amount ?? 0 : a.estimated_cost ?? 0;
  const tooMuch = isPay && cash !== null && amount > cash.balance;
  const due = a.days_until_due;

  useEffect(() => {
    if (!confirming) return;
    const t = window.setTimeout(() => setConfirming(false), 5000);
    return () => window.clearTimeout(t);
  }, [confirming]);

  async function click() {
    if (!name) return;
    if (!confirming) return setConfirming(true);
    setBusy(true);
    await onApprove(a, name);
    setBusy(false);
    setConfirming(false);
  }

  return (
    <article className={`approval ${highlight ? "highlight" : ""}`}>
      <div className="approval-top">
        <span className="approval-kind">{isPay ? (a.kind === "rent" ? "Rent payment" : "Invoice payment") : "Purchase order"}</span>
        <span className="pill-soft">{a.id} · #{a.ticket_id}</span>
      </div>
      <h4>{isPay ? `Pay ${a.payee}` : `Order ${a.qty} × ${a.sku} ${a.size}`}</h4>
      <div className="approval-amount">
        {money(amount)}
        {isPay && due !== undefined && (
          <span className={`pill-black ${due < 0 ? "late" : ""}`}>{due < 0 ? `${-due}d overdue` : due === 0 ? "due today" : `due in ${due}d`}</span>
        )}
        {!isPay && <span className="pill-black">ETA {a.eta_if_approved_today}</span>}
      </div>
      <p className="approval-desc">{isPay ? a.description : `From ${a.vendor}${a.will_ship ? "" : " — blocked until its open invoice is paid"}`}</p>
      <div className="approval-why">
        <Avatar role={a.prepared_by} size={30} />
        <p>
          <strong>{AGENT_BY_KEY[a.prepared_by]?.name ?? a.prepared_by}:</strong> {a.reason}
        </p>
      </div>
      {isPay && cash && !tooMuch && (
        <p className="approval-after">Checking after: {money(cash.balance - amount)}</p>
      )}
      {tooMuch && <p className="approval-warn">Not enough cash — the pay tool will refuse this.</p>}
      <div className="approval-actions">
        <button className="btn-ghost" disabled={!name || busy || teamBusy} onClick={() => onReject(a, name)}>
          Reject
        </button>
        <button className={`btn-black ${confirming ? "confirming" : ""}`} disabled={!name || busy || teamBusy} onClick={click}>
          {busy ? <span className="spinner" /> : teamBusy ? "Wait — the team is working" : !name ? "Add your name to approve" : confirming
            ? `Tap again to ${isPay ? "pay" : "approve"} ${money(amount)}`
            : isPay ? `Approve & pay ${money(amount)}` : "Approve order"}
        </button>
      </div>
    </article>
  );
}
