"""Campus Customs MCP — the only source of shop facts for the agent team.

Reads and writes ../data/campus_customs_new.db (the working copy). The original
campus_customs.db is never written; reset_database() copies it back over the
working copy before a full run.

Tool groups:
  - Read tools (open the DB read-only): tickets, inventory, pricing, cash,
    invoices, vendors, leases, payments, obligations, approval queue, drafts.
  - Agent write tools: prepare_payment / prepare_purchase_order (queue a request
    for a human; no money moves), draft_customer_message (saved, never sent),
    update_ticket_status.
  - Human-only tools (tag "human_only"; never given to an agent): pay,
    approve_purchase_order, reject_request, reset_database.

The approval queue and message drafts are workflow state, not shop facts, so
they live in ../output/approvals.json and ../output/drafts.json.

Run from this folder (stdio):  python server.py
Run (HTTP):                    python server.py --http
HTTP URL:                      http://127.0.0.1:8002/mcp
"""

from __future__ import annotations

import argparse
import calendar
import fcntl
import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# Env overrides exist only so tests can point at a scratch copy.
DB_PATH = Path(os.getenv("CAMPUS_DB_PATH", ROOT / "data" / "campus_customs_new.db"))
ORIGINAL_DB_PATH = Path(os.getenv("CAMPUS_ORIGINAL_DB_PATH", ROOT / "data" / "campus_customs.db"))
OUTPUT_DIR = Path(os.getenv("CAMPUS_OUTPUT_DIR", ROOT / "output"))
APPROVALS_PATH = OUTPUT_DIR / "approvals.json"
DRAFTS_PATH = OUTPUT_DIR / "drafts.json"

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service", "customer service"}
TICKET_STATUSES = {"open", "in_progress", "waiting_on_approval", "resolved"}
PAYMENT_KINDS = {"invoice", "rent"}

mcp = FastMCP("campus-customs")


# ---------- helpers ----------

def _connect() -> sqlite3.Connection:
    """Open the working database read-only so read tools can never change it."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_rw() -> sqlite3.Connection:
    """Read-write connection, used only by the guarded write tools."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _today(conn: sqlite3.Connection) -> date:
    return date.fromisoformat(conn.execute("SELECT date_today FROM desk").fetchone()["date_today"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _add_month(d: date) -> date:
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


@contextmanager
def _locked_json(path: Path) -> Iterator[list[dict[str, Any]]]:
    """Load a JSON list under an exclusive file lock and write it back on exit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(f".{path.stem}.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        items = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else []
        yield items
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, indent=2))
        tmp.replace(path)


def _read_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text()) if path.exists() and path.read_text().strip() else []


def _is_agent_name(name: str) -> bool:
    n = name.strip().lower()
    return not n or n in AGENT_NAMES or "agent" in n


def _obligation(conn: sqlite3.Connection, kind: str, ref_id: int) -> dict[str, Any] | None:
    """Look up what is actually owed for a rent lease or a vendor invoice."""
    if kind == "invoice":
        row = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (ref_id,),
        ).fetchone()
        if row is None:
            return None
        return {"kind": "invoice", "ref_id": row["id"], "amount": row["amount"], "payee": row["vendor_name"],
                "due_date": row["due_date"], "open": row["status"] == "open", "description": row["description"]}
    if kind == "rent":
        row = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
        if row is None:
            return None
        return {"kind": "rent", "ref_id": row["id"], "amount": row["monthly_rent"], "payee": row["landlord"],
                "due_date": row["next_due"], "open": True, "description": f"Rent for {row['space_name']}"}
    return None


def _pending_payment_total(account: str) -> float:
    return round(sum(a["amount"] for a in _read_json(APPROVALS_PATH)
                     if a["type"] == "payment" and a["status"] == "pending" and a["account"] == account), 2)


# ---------- read tools: original three ----------

@mcp.tool
def check_inventory(sku: str, size: str | None = None, qty_requested: int | None = None) -> dict:
    """Check whether we stock an item and how many are on hand.

    Give a SKU (e.g. "CC-TEE-WHITE"), optionally a size ("S", "M", "L",
    "XL", or "OS") and the quantity the customer wants. Returns every size
    we carry for that SKU, the on-hand count for the requested size, and
    whether the request can be filled from stock right now.
    """
    sku = sku.strip().upper()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid",
            (sku,),
        ).fetchall()
    if not rows:
        return {"sku": sku, "stocked": False, "message": f"We do not carry {sku}."}

    result = {
        "sku": sku,
        "name": rows[0]["name"],
        "stocked": True,
        "sizes": [{"size": r["size"], "qty": r["qty"], "location": r["location"]} for r in rows],
        "total_on_hand": sum(r["qty"] for r in rows),
    }
    if size is None:
        return result

    size = size.strip().upper()
    match = next((r for r in rows if r["size"] == size), None)
    if match is None:
        result.update(size=size, size_stocked=False, message=f"We do not carry {sku} in size {size}.")
        return result

    on_hand = match["qty"]
    result.update(size=size, size_stocked=True, on_hand=on_hand, in_stock=on_hand > 0)
    if qty_requested is not None:
        shortfall = max(qty_requested - on_hand, 0)
        result.update(
            qty_requested=qty_requested,
            can_fulfill=shortfall == 0,
            shortfall=shortfall,
        )
    return result


@mcp.tool
def check_overdue(ticket_id: int) -> dict:
    """Check whether the bill tied to a ticket is overdue as of desk.date_today.

    Looks at the ticket type and pulls the right due date:
      - rent_notice     -> leases.next_due (via ticket.lease_id)
      - any ticket with an invoice_id -> invoices.due_date
      - price_override (no lease/invoice) -> no due date; cannot be overdue
    Days are counted against desk.date_today, not the real-world clock.
    """
    with _connect() as conn:
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"ticket_id": ticket_id, "error": f"No ticket with id {ticket_id}."}
        today_str = conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]

        source = None
        if ticket["type"] == "rent_notice" and ticket["lease_id"] is not None:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
            if lease is not None:
                source = {
                    "table": "leases",
                    "id": lease["id"],
                    "due_date": lease["next_due"],
                    "amount": lease["monthly_rent"],
                    "payee": lease["landlord"],
                    "paid": False,
                }
        elif ticket["invoice_id"] is not None:
            inv = conn.execute(
                """
                SELECT i.*, v.name AS vendor_name
                FROM invoices i JOIN vendors v ON v.id = i.vendor_id
                WHERE i.id = ?
                """,
                (ticket["invoice_id"],),
            ).fetchone()
            if inv is not None:
                source = {
                    "table": "invoices",
                    "id": inv["id"],
                    "due_date": inv["due_date"],
                    "amount": inv["amount"],
                    "payee": inv["vendor_name"],
                    "description": inv["description"],
                    "paid": inv["status"] != "open",
                }

    result = {"ticket_id": ticket_id, "ticket_type": ticket["type"], "date_today": today_str}
    if source is None:
        result.update(can_be_overdue=False, message="This ticket has no lease or invoice, so it has no due date.")
        return result

    days_until_due = (date.fromisoformat(source["due_date"]) - date.fromisoformat(today_str)).days
    overdue = days_until_due < 0 and not source["paid"]
    result.update(
        can_be_overdue=True,
        source=source,
        days_until_due=days_until_due,
        overdue=overdue,
        days_overdue=-days_until_due if overdue else 0,
    )
    return result


@mcp.tool
def check_price(sku: str, proposed_unit_price: float | None = None, qty: int | None = None) -> dict:
    """Look up an item's cost and list price to see how far it can be discounted.

    Give a SKU and, optionally, a proposed per-unit price and quantity for a
    discount request. Returns list price, unit cost, margin, the maximum
    discount that still breaks even, and (if a price is proposed) whether
    that price is above cost and what the order would earn.
    """
    sku = sku.strip().upper()
    with _connect() as conn:
        row = conn.execute("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if row is None:
        return {"sku": sku, "priced": False, "message": f"No pricing for {sku}; we do not stock it."}

    cost, list_price = row["unit_cost"], row["list_price"]
    result = {
        "sku": sku,
        "priced": True,
        "unit_cost": cost,
        "list_price": list_price,
        "margin_per_unit": round(list_price - cost, 2),
        "margin_pct": round((list_price - cost) / list_price * 100, 1),
        "max_discount_pct_to_break_even": round((list_price - cost) / list_price * 100, 1),
        "discountable": list_price > cost,
    }
    if proposed_unit_price is not None:
        result.update(
            proposed_unit_price=proposed_unit_price,
            discount_pct=round((list_price - proposed_unit_price) / list_price * 100, 1),
            above_cost=proposed_unit_price > cost,
            profit_per_unit=round(proposed_unit_price - cost, 2),
        )
        if qty is not None:
            result.update(
                qty=qty,
                order_revenue=round(proposed_unit_price * qty, 2),
                order_profit=round((proposed_unit_price - cost) * qty, 2),
            )
    return result


# ---------- read tools: added in Problem 5 ----------

@mcp.tool
def get_desk_today() -> dict:
    """Return the shop's "today" (desk.date_today). Use this, never the real clock, for due dates."""
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk").fetchone()
    return {"date_today": row["date_today"], "notes": row["notes"]}


@mcp.tool
def list_tickets(status: str | None = "open") -> dict:
    """List tickets in the queue. Pass status="open" (default), another status, or null for all."""
    with _connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM tickets WHERE status = ? ORDER BY id", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    return {"status_filter": status, "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Read one ticket plus the lease or invoice (with vendor) it links to."""
    with _connect() as conn:
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"ticket_id": ticket_id, "error": f"No ticket with id {ticket_id}."}
        result: dict[str, Any] = {"ticket": dict(ticket)}
        if ticket["lease_id"] is not None:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
            result["linked_lease"] = dict(lease) if lease else None
        if ticket["invoice_id"] is not None:
            inv = conn.execute(
                "SELECT i.*, v.name AS vendor_name, v.lead_days FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ticket["invoice_id"],),
            ).fetchone()
            result["linked_invoice"] = dict(inv) if inv else None
    return result


@mcp.tool
def get_cash_balance() -> dict:
    """Cash on hand per account, minus payments already waiting for human approval."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM cash_accounts ORDER BY name").fetchall()
    accounts = []
    for r in rows:
        pending = _pending_payment_total(r["name"])
        accounts.append({"name": r["name"], "balance": r["balance"], "as_of": r["date"],
                         "pending_approval_payments": pending,
                         "available_after_pending": round(r["balance"] - pending, 2)})
    return {"accounts": accounts, "note": "Cash only goes out. There is no tool that adds money."}


@mcp.tool
def list_invoices(status: str | None = None) -> dict:
    """List vendor invoices (optionally only "open" or "paid") with days until due / overdue vs desk.date_today."""
    with _connect() as conn:
        today = _today(conn)
        sql = "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id"
        rows = conn.execute(sql + (" WHERE i.status = ?" if status else "") + " ORDER BY i.due_date",
                            (status,) if status else ()).fetchall()
    out = []
    for r in rows:
        days = (date.fromisoformat(r["due_date"]) - today).days
        out.append({**dict(r), "days_until_due": days, "overdue": r["status"] == "open" and days < 0})
    return {"date_today": today.isoformat(), "invoices": out}


@mcp.tool
def list_vendors() -> dict:
    """List vendors with lead time, open unpaid invoices, and whether they will ship new product.

    Shop rule: a vendor will not ship new product while it has an open unpaid
    invoice. eta_if_ordered_today = desk.date_today + vendors.lead_days.
    """
    with _connect() as conn:
        today = _today(conn)
        vendors = conn.execute("SELECT * FROM vendors ORDER BY id").fetchall()
        out = []
        for v in vendors:
            open_inv = conn.execute(
                "SELECT id, amount, due_date, description FROM invoices WHERE vendor_id = ? AND status = 'open'",
                (v["id"],),
            ).fetchall()
            out.append({
                **dict(v),
                "open_invoices": [dict(i) for i in open_inv],
                "open_invoice_total": round(sum(i["amount"] for i in open_inv), 2),
                "will_ship_new_product": not open_inv,
                "eta_if_ordered_today": (today + timedelta(days=v["lead_days"])).isoformat(),
            })
    return {"date_today": today.isoformat(), "vendors": out}


@mcp.tool
def list_leases() -> dict:
    """List shop leases with rent amount, next due date, and days until due vs desk.date_today."""
    with _connect() as conn:
        today = _today(conn)
        rows = conn.execute("SELECT * FROM leases ORDER BY id").fetchall()
    return {"date_today": today.isoformat(), "leases": [
        {**dict(r), "days_until_due": (date.fromisoformat(r["next_due"]) - today).days} for r in rows]}


@mcp.tool
def list_payments() -> dict:
    """List payments already made (the money-out ledger)."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM payments ORDER BY id").fetchall()
    return {"payments": [dict(r) for r in rows]}


@mcp.tool
def list_obligations(within_days: int = 30) -> dict:
    """Everything the shop owes soon (open invoices + rent due within N days) against cash.

    Shows total owed, cash on hand, payments already waiting for approval, and
    the cash left if everything were paid, so the team can prioritize.
    """
    with _connect() as conn:
        today = _today(conn)
        items = []
        for r in conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.status = 'open'"
        ).fetchall():
            days = (date.fromisoformat(r["due_date"]) - today).days
            items.append({"kind": "invoice", "ref_id": r["id"], "payee": r["vendor_name"], "amount": r["amount"],
                          "due_date": r["due_date"], "days_until_due": days, "overdue": days < 0,
                          "description": r["description"]})
        for r in conn.execute("SELECT * FROM leases").fetchall():
            days = (date.fromisoformat(r["next_due"]) - today).days
            if days <= within_days:
                items.append({"kind": "rent", "ref_id": r["id"], "payee": r["landlord"], "amount": r["monthly_rent"],
                              "due_date": r["next_due"], "days_until_due": days, "overdue": days < 0,
                              "description": f"Rent for {r['space_name']}"})
        cash = conn.execute("SELECT COALESCE(SUM(balance), 0) AS c FROM cash_accounts").fetchone()["c"]
    items.sort(key=lambda x: x["due_date"])
    total = round(sum(i["amount"] for i in items), 2)
    return {"date_today": today.isoformat(), "obligations": items, "total_owed": total, "cash_on_hand": cash,
            "cash_left_if_all_paid": round(cash - total, 2), "can_cover_all": cash >= total}


@mcp.tool
def list_approvals(status: str | None = "pending") -> dict:
    """List payment / purchase-order requests in the human approval queue (default: pending only)."""
    items = _read_json(APPROVALS_PATH)
    return {"approvals": [a for a in items if status is None or a["status"] == status]}


@mcp.tool
def list_drafts(ticket_id: int | None = None) -> dict:
    """List customer/vendor message drafts on the board. Drafts are never sent."""
    items = _read_json(DRAFTS_PATH)
    return {"drafts": [d for d in items if ticket_id is None or d["ticket_id"] == ticket_id]}


# ---------- agent write tools (queue / draft only; no money moves) ----------

@mcp.tool
def prepare_payment(kind: str, ref_id: int, prepared_by: str, reason: str,
                    ticket_id: int | None = None, account: str = "checking") -> dict:
    """Queue a payment for HUMAN approval. Does not move money.

    kind: "invoice" (ref_id = invoices.id) or "rent" (ref_id = leases.id).
    The amount is taken from the database, not from the caller. Refuses if
    the bill is already paid, already queued, or cash (after other pending
    payments) cannot cover it.
    """
    kind = kind.strip().lower()
    if kind not in PAYMENT_KINDS:
        return {"queued": False, "error": f"kind must be one of {sorted(PAYMENT_KINDS)}."}
    with _connect() as conn:
        ob = _obligation(conn, kind, ref_id)
        acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        today = _today(conn)
    if ob is None:
        return {"queued": False, "error": f"No {kind} with id {ref_id}."}
    if not ob["open"]:
        return {"queued": False, "error": f"{kind} {ref_id} is already paid."}
    if acct is None:
        return {"queued": False, "error": f"No cash account named {account!r}."}

    with _locked_json(APPROVALS_PATH) as items:
        dup = next((a for a in items if a["type"] == "payment" and a["kind"] == kind and a["ref_id"] == ref_id
                    and a["due_date"] == ob["due_date"] and a["status"] in ("pending", "paid")), None)
        if dup:
            return {"queued": False, "already_requested": True, "approval": dup}
        pending = round(sum(a["amount"] for a in items
                            if a["type"] == "payment" and a["status"] == "pending" and a["account"] == account), 2)
        available = round(acct["balance"] - pending, 2)
        if ob["amount"] > available:
            return {"queued": False, "error": "Insufficient cash after payments already awaiting approval.",
                    "amount": ob["amount"], "balance": acct["balance"], "pending_payments": pending,
                    "available": available}
        approval = {
            "id": f"PAY-{len(items) + 1:03d}",
            "type": "payment",
            "status": "pending",
            "kind": kind,
            "ref_id": ref_id,
            "ticket_id": ticket_id,
            "payee": ob["payee"],
            "amount": ob["amount"],
            "account": account,
            "due_date": ob["due_date"],
            "days_until_due": (date.fromisoformat(ob["due_date"]) - today).days,
            "description": ob["description"],
            "reason": reason,
            "prepared_by": prepared_by,
            "prepared_at": _now(),
            "balance_now": acct["balance"],
            "balance_after_if_approved": round(available - ob["amount"], 2),
        }
        items.append(approval)
    return {"queued": True, "approval": approval,
            "message": "Waiting for human approval. No money has moved."}


@mcp.tool
def prepare_purchase_order(vendor_id: int, sku: str, size: str, qty: int, prepared_by: str, reason: str,
                           ticket_id: int | None = None) -> dict:
    """Queue a restock purchase order for HUMAN approval. Nothing is sent to the vendor.

    Estimates cost from pricing.unit_cost, ETA from vendors.lead_days, and flags
    whether the vendor is blocked by an open unpaid invoice.
    """
    sku, size = sku.strip().upper(), size.strip().upper()
    if qty <= 0:
        return {"queued": False, "error": "qty must be positive."}
    with _connect() as conn:
        today = _today(conn)
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        item = conn.execute("SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        open_inv = conn.execute("SELECT id, amount FROM invoices WHERE vendor_id = ? AND status = 'open'",
                                (vendor_id,)).fetchall()
    if vendor is None:
        return {"queued": False, "error": f"No vendor with id {vendor_id}."}
    if price is None or item is None:
        return {"queued": False, "error": f"We do not carry {sku} in size {size}."}

    blocked = bool(open_inv)
    with _locked_json(APPROVALS_PATH) as items:
        approval = {
            "id": f"PO-{len(items) + 1:03d}",
            "type": "purchase_order",
            "status": "pending",
            "ticket_id": ticket_id,
            "vendor_id": vendor_id,
            "vendor": vendor["name"],
            "sku": sku,
            "size": size,
            "qty": qty,
            "unit_cost": price["unit_cost"],
            "estimated_cost": round(price["unit_cost"] * qty, 2),
            "lead_days": vendor["lead_days"],
            "eta_if_approved_today": (today + timedelta(days=vendor["lead_days"])).isoformat(),
            "vendor_blocked_by_open_invoices": [dict(i) for i in open_inv],
            "will_ship": not blocked,
            "reason": reason,
            "prepared_by": prepared_by,
            "prepared_at": _now(),
        }
        items.append(approval)
    msg = "Waiting for human approval. Nothing has been sent to the vendor."
    if blocked:
        msg += " Vendor will not ship until its open invoice(s) are paid."
    return {"queued": True, "approval": approval, "message": msg}


@mcp.tool
def draft_customer_message(ticket_id: int, to: str, subject: str, body: str, drafted_by: str) -> dict:
    """Save a message draft to the board for a human to review. It is NEVER emailed, texted, or called."""
    with _locked_json(DRAFTS_PATH) as items:
        draft = {
            "id": f"DRAFT-{len(items) + 1:03d}",
            "ticket_id": ticket_id,
            "to": to,
            "subject": subject,
            "body": body,
            "drafted_by": drafted_by,
            "drafted_at": _now(),
            "status": "draft (not sent)",
        }
        items.append(draft)
    return {"saved": True, "sent": False, "draft": draft}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str) -> dict:
    """Set tickets.status to open, in_progress, waiting_on_approval, or resolved."""
    if status not in TICKET_STATUSES:
        return {"updated": False, "error": f"status must be one of {sorted(TICKET_STATUSES)}."}
    with _connect_rw() as conn:
        cur = conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
    conn.close()
    if cur.rowcount == 0:
        return {"updated": False, "error": f"No ticket with id {ticket_id}."}
    return {"updated": True, "ticket_id": ticket_id, "status": status}


# ---------- human-only tools (never exposed to agents) ----------

@mcp.tool(tags={"human_only"})
def pay(approval_id: str, approved_by: str) -> dict:
    """HUMAN ONLY. Execute a queued payment after a person approves it.

    Re-checks the bill and the balance, then in one transaction: inserts a
    payments row, lowers cash_accounts.balance, and marks the invoice paid or
    moves the lease's next_due forward one month. Refuses if cash is short, so
    a balance can never go negative.
    """
    if _is_agent_name(approved_by):
        return {"paid": False, "error": "approved_by must be a named human, not an agent."}
    with _locked_json(APPROVALS_PATH) as items:
        req = next((a for a in items if a["id"] == approval_id and a["type"] == "payment"), None)
        if req is None:
            return {"paid": False, "error": f"No payment request {approval_id}."}
        if req["status"] != "pending":
            return {"paid": False, "error": f"{approval_id} is already {req['status']}."}

        conn = _connect_rw()
        try:
            conn.execute("BEGIN IMMEDIATE")
            today = _today(conn)
            ob = _obligation(conn, req["kind"], req["ref_id"])
            if ob is None or not ob["open"] or ob["due_date"] != req["due_date"]:
                conn.rollback()
                return {"paid": False, "error": "Bill changed or was already paid since the request was made."}
            amount = ob["amount"]
            if amount <= 0:
                conn.rollback()
                return {"paid": False, "error": "Only positive payments out are allowed."}
            acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (req["account"],)).fetchone()
            if acct is None or acct["balance"] < amount:
                conn.rollback()
                return {"paid": False, "error": "Insufficient cash. Payment refused.",
                        "balance": acct["balance"] if acct else None, "amount": amount}
            new_balance = round(acct["balance"] - amount, 2)
            conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                         (new_balance, today.isoformat(), req["account"]))
            cur = conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                (req["kind"], req["ref_id"], amount, req["account"], today.isoformat(), approved_by.strip()),
            )
            payment_id = cur.lastrowid
            if req["kind"] == "invoice":
                conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
                updated = {"table": "invoices", "id": req["ref_id"], "status": "paid"}
            else:
                next_due = _add_month(date.fromisoformat(ob["due_date"])).isoformat()
                conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, req["ref_id"]))
                updated = {"table": "leases", "id": req["ref_id"], "next_due": next_due}
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        req.update(status="paid", approved_by=approved_by.strip(), decided_at=_now(), payment_id=payment_id,
                   balance_after=new_balance)
    return {"paid": True, "payment_id": payment_id, "amount": amount, "account": req["account"],
            "balance_after": new_balance, "updated": updated, "approval": req}


@mcp.tool(tags={"human_only"})
def approve_purchase_order(approval_id: str, approved_by: str) -> dict:
    """HUMAN ONLY. Mark a queued purchase order approved. Nothing is sent; a person places the order."""
    if _is_agent_name(approved_by):
        return {"approved": False, "error": "approved_by must be a named human, not an agent."}
    with _locked_json(APPROVALS_PATH) as items:
        req = next((a for a in items if a["id"] == approval_id and a["type"] == "purchase_order"), None)
        if req is None:
            return {"approved": False, "error": f"No purchase order {approval_id}."}
        if req["status"] != "pending":
            return {"approved": False, "error": f"{approval_id} is already {req['status']}."}
        req.update(status="approved", approved_by=approved_by.strip(), decided_at=_now())
    return {"approved": True, "approval": req,
            "message": "Approved. Not sent to the vendor; a person places the order."}


@mcp.tool(tags={"human_only"})
def reject_request(approval_id: str, rejected_by: str, reason: str = "") -> dict:
    """HUMAN ONLY. Reject a pending payment or purchase order."""
    if _is_agent_name(rejected_by):
        return {"rejected": False, "error": "rejected_by must be a named human, not an agent."}
    with _locked_json(APPROVALS_PATH) as items:
        req = next((a for a in items if a["id"] == approval_id), None)
        if req is None or req["status"] != "pending":
            return {"rejected": False, "error": f"{approval_id} is not a pending request."}
        req.update(status="rejected", rejected_by=rejected_by.strip(), reject_reason=reason, decided_at=_now())
    return {"rejected": True, "approval": req}


@mcp.tool(tags={"human_only"})
def reset_database() -> dict:
    """HUMAN / RUNNER ONLY. Copy campus_customs.db over the working copy and clear the approval queue and drafts.

    Run this before every full ticket run. The audit trail is never cleared.
    """
    shutil.copyfile(ORIGINAL_DB_PATH, DB_PATH)
    for path in (APPROVALS_PATH, DRAFTS_PATH):
        with _locked_json(path) as items:
            items.clear()
    with _connect() as conn:
        counts = {t: conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                  for t in ("tickets", "invoices", "payments")}
        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()["balance"]
    return {"reset": True, "database": str(DB_PATH.name), "from": str(ORIGINAL_DB_PATH.name),
            "row_counts": counts, "checking_balance": cash, "approvals_cleared": True, "drafts_cleared": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs MCP server")
    parser.add_argument("--http", action="store_true", help="Serve over HTTP instead of stdio")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8002)
    else:
        mcp.run(show_banner=False, log_level="WARNING")
