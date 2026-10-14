import { useState } from "react";
import type { Ticket } from "../types";
import TicketArt from "./TicketArt";

type Filter = "all" | "open" | "resolved";

function headline(t: Ticket): string {
  if (t.type === "rent_notice") return `Lease #${t.lease_id ?? "?"}`;
  const item = t.sku?.includes("HOOD") ? "Hoodie" : t.sku?.includes("TEE") ? "Tee" : t.sku ?? "Item";
  return `${t.qty ?? 1} × ${item} · ${t.size ?? ""}`;
}

const TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price override",
};

export default function TicketsPanel({
  tickets,
  selected,
  onSelect,
  pendingByTicket,
  runningTicket,
}: {
  tickets: Ticket[];
  selected: number | null;
  onSelect: (id: number) => void;
  pendingByTicket: Record<number, number>;
  runningTicket: number | null;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const shown = tickets.filter((t) => filter === "all" || t.state === filter);
  const pendingTotal = Object.values(pendingByTicket).reduce((a, b) => a + b, 0);

  return (
    <section className="panel panel-light tickets-panel" id="tickets">
      <div className="panel-head">
        <h2>Tickets</h2>
        <div className="icon-btn soft" title={`${pendingTotal} waiting for your approval`}>
          <BellIcon />
          {pendingTotal > 0 && <span className="dot-badge">{pendingTotal}</span>}
        </div>
      </div>

      <div className="chips">
        {(["all", "open", "resolved"] as Filter[]).map((f) => (
          <button key={f} className={`chip ${filter === f ? "chip-on" : ""}`} onClick={() => setFilter(f)}>
            {f === "all" ? "All" : f === "open" ? "Open" : "Resolved"}
            <span className="chip-count">{f === "all" ? tickets.length : tickets.filter((t) => t.state === f).length}</span>
          </button>
        ))}
      </div>

      <p className="panel-hint">Click a ticket to open it on the left, then press the green button there to start.</p>

      <div className="ticket-list">
        {shown.map((t) => (
          <div
            key={t.id}
            role="button"
            tabIndex={0}
            aria-pressed={selected === t.id}
            className={`ticket-card ${selected === t.id ? "is-selected" : ""} ${t.state === "resolved" ? "is-resolved" : ""}`}
            onClick={() => onSelect(t.id)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(t.id)}
          >
            <div className="ticket-art-wrap">
              <TicketArt type={t.type} size={66} />
            </div>
            <span className="pill-black ticket-id">#{t.id}</span>
            <div className="ticket-body">
              <span className="ticket-type">{TYPE_LABEL[t.type] ?? t.type}</span>
              <strong className="ticket-subject">{t.subject}</strong>
              <span className="ticket-requester">{t.requester}</span>
              <span className="ticket-headline">{headline(t)}</span>
            </div>
            <div className="ticket-foot">
              {runningTicket === t.id ? (
                <span className="status-pill working"><span className="spinner" /> Team working</span>
              ) : t.state === "resolved" ? (
                <span className="status-pill resolved">✓ Resolved</span>
              ) : (
                <span className="status-pill open">Open</span>
              )}
              {pendingByTicket[t.id] > 0 && <span className="status-pill needs-ok">{pendingByTicket[t.id]} needs your OK</span>}
            </div>
            {t.state === "resolved" && <span className="stamp">Resolved</span>}
            {selected === t.id && <span className="selected-tag">Selected</span>}
          </div>
        ))}
        {shown.length === 0 && <p className="empty">No {filter} tickets.</p>}
      </div>
    </section>
  );
}

const BellIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1Z" />
  </svg>
);
