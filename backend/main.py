"""FastAPI backend for the Campus Customs ticket board.

Start from the backend/ folder:
    uvicorn main:app --reload --port 8000

Every shop fact comes from the campus-customs MCP server (one stdio connection
opened at startup). Agent runs happen in the background so the board can poll
/api/events while the team works. Money only moves through
POST /api/approvals/{id}/approve, which a person triggers by clicking Approve.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from audit import AuditTrail
from config import AUDIT_TRAIL_PATH, MODEL_NAME
from mcp_client import call_mcp, campus_customs
from run_tickets import new_run_id, run_team

# One team run at a time: runs, approvals, and resets all touch the same DB and queue.
_team_lock = asyncio.Lock()
RUNS: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with campus_customs:  # keep one MCP server process alive for the app's lifetime
        yield


app = FastAPI(title="Campus Customs Ticket Board API", lifespan=lifespan)
# Only local pages may call this API (a random website must not be able to click "approve").
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # the Vite dashboard (npm run dev)
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",  # other local dev ports
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _require_idle(action: str) -> None:
    if _team_lock.locked() or any(r["status"] == "running" for r in RUNS.values()):
        raise HTTPException(409, f"An agent run is in progress; try {action} when it finishes.")


# ---------- tickets ----------

@app.get("/api/tickets")
async def list_tickets() -> dict[str, Any]:
    """All tickets and whether each is open or resolved."""
    tickets = (await call_mcp("list_tickets", {"status": None}))["tickets"]
    return {"tickets": [
        {"id": t["id"], "type": t["type"], "requester": t["requester"], "subject": t["subject"],
         "sku": t["sku"], "size": t["size"], "qty": t["qty"], "lease_id": t["lease_id"],
         "invoice_id": t["invoice_id"], "notes": t["notes"],
         "status": t["status"], "state": "resolved" if t["status"] == "resolved" else "open"}
        for t in tickets
    ]}


async def _run_in_background(run_id: str, ticket_id: int) -> None:
    run = RUNS[run_id]
    try:
        async with _team_lock:
            team = await run_team(reset=False, ticket_ids=[ticket_id], run_id=run_id)
        result = team.tickets[0] if team.tickets else None
        if result is not None and result.error is None:
            # The team's work on the ticket is done, so the board shows it resolved. Any payment or
            # purchase order it queued stays in the approval queue until a person decides.
            marked = await call_mcp("update_ticket_status", {"ticket_id": ticket_id, "status": "resolved"})
            AuditTrail(run_id).log("ticket_marked_resolved", agent=None, ticket_id=ticket_id, result=marked)
        run.update(status="error" if result is None or result.error else "done",
                   result=result.model_dump(mode="json") if result else None,
                   pending_approvals=team.pending_approvals, usage=team.usage)
    except Exception as exc:
        run.update(status="error", error=f"{type(exc).__name__}: {exc}")
    run["finished_at"] = _now()


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    """Start the agent team on one ticket. Returns a run_id right away; poll /api/events or /api/runs/{run_id}."""
    _require_idle("another run")
    found = await call_mcp("get_ticket", {"ticket_id": ticket_id})
    if "ticket" not in found:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if found["ticket"]["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved. Reset the database for a fresh run.")

    run_id = new_run_id()
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running", "model": MODEL_NAME,
                    "started_at": _now(), "finished_at": None}
    RUNS[run_id]["task"] = asyncio.create_task(_run_in_background(run_id, ticket_id))
    return {k: v for k, v in RUNS[run_id].items() if k != "task"}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Status of a run started from this server, with the Boss's decision once it is done."""
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} on this server.")
    return {k: v for k, v in RUNS[run_id].items() if k != "task"}


# ---------- agent events ----------

def _summarize(e: dict[str, Any]) -> dict[str, Any]:
    """Turn one audit event into what the board shows: who, what they said, which tools."""
    d = e.get("data", {})
    step = e["step"]
    said, tools, detail = None, [], None
    if step == "model_response":
        said = d.get("text") or None
        tools = [c["tool"] for c in d.get("tool_calls", [])]
    elif step in ("tool_call", "tool_result", "tool_refused", "tool_error"):
        tools = [d.get("tool")]
        detail = d.get("args") if step == "tool_call" else (d.get("result") or d.get("error"))
    elif step == "delegation_start":
        said = f"→ {d.get('to_agent')}: {d.get('task')}"
        tools = ["ask_agent"]
    elif step == "delegation_end":
        report = d.get("report") or {}
        said = f"← {d.get('to_agent')} ({d.get('status')}): {report.get('summary') or d.get('error') or ''}"
    elif step == "delegation_refused":
        said = f"✕ {d.get('to_agent')}: {d.get('reason')}"
    elif step == "run_start":
        said = d.get("prompt")
    elif step == "run_end":
        out = d.get("output") or {}
        said = out.get("decision") or out.get("summary")
    elif step in ("run_error", "ticket_end") and d.get("error"):
        said = d.get("error")
    elif step == "human_decision":
        said = f"{d.get('human')} → {d.get('tool')} {d.get('approval_id')}"
    if isinstance(detail, str) and len(detail) > 600:
        detail = detail[:600] + "…"
    return {"run_id": e["run_id"], "seq": e["seq"], "ts": e["ts"], "ticket_id": e.get("ticket_id"),
            "agent": e.get("agent"), "depth": e.get("depth"), "parent_agent": e.get("parent_agent"),
            "step": step, "said": said, "tools": [t for t in tools if t], "detail": detail}


@app.get("/api/events")
async def recent_events(
    limit: int = Query(100, ge=1, le=1000),
    after: int | None = Query(None, description="Only events after this id (for polling)."),
    run_id: str | None = None,
    ticket_id: int | None = None,
) -> dict[str, Any]:
    """Recent agent events from output/audit_trail.json: what each agent said and which tools it used."""
    text = AUDIT_TRAIL_PATH.read_text() if AUDIT_TRAIL_PATH.exists() else ""
    events = json.loads(text) if text.strip() else []
    rows = [{"id": i, **_summarize(e)} for i, e in enumerate(events)
            if (after is None or i > after)
            and (run_id is None or e["run_id"] == run_id)
            and (ticket_id is None or e.get("ticket_id") == ticket_id)]
    rows = rows[-limit:]
    return {"events": rows, "last_id": len(events) - 1, "running": _team_lock.locked()}


# ---------- approvals (human only) ----------

class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the person approving.")


class RejectBody(BaseModel):
    rejected_by: str = Field(min_length=1)
    reason: str = ""


@app.get("/api/approvals")
async def list_approvals(status: str | None = "pending") -> dict[str, Any]:
    """Payments and purchase orders the agents queued. Pass status=all for every request."""
    return await call_mcp("list_approvals", {"status": None if status == "all" else status})


def _raise_if_refused(result: dict[str, Any]) -> None:
    if result.get("error"):
        code = 404 if result["error"].startswith("No ") else 409
        raise HTTPException(code, result["error"])


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: str, body: ApproveBody) -> dict[str, Any]:
    """A person clicked Approve. Payments run the MCP `pay` tool (the only thing that changes cash);
    purchase orders are marked approved (nothing is sent to the vendor)."""
    _require_idle("approving")
    tool = "pay" if approval_id.upper().startswith("PAY-") else "approve_purchase_order"
    result = await call_mcp(tool, {"approval_id": approval_id, "approved_by": body.approved_by})
    AuditTrail(f"human-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}").log(
        "human_decision", ticket_id=(result.get("approval") or {}).get("ticket_id"), human=body.approved_by,
        approval_id=approval_id, tool=tool, result=result)
    _raise_if_refused(result)
    return result


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: str, body: RejectBody) -> dict[str, Any]:
    """A person clicked Reject."""
    result = await call_mcp("reject_request", {"approval_id": approval_id, "rejected_by": body.rejected_by,
                                               "reason": body.reason})
    AuditTrail(f"human-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}").log(
        "human_decision", ticket_id=(result.get("approval") or {}).get("ticket_id"), human=body.rejected_by,
        approval_id=approval_id, tool="reject_request", result=result)
    _raise_if_refused(result)
    return result


# ---------- cash, drafts, reset ----------

@app.get("/api/cash")
async def cash() -> dict[str, Any]:
    """Current checking balance from cash_accounts (plus payments still waiting for approval)."""
    accounts = (await call_mcp("get_cash_balance"))["accounts"]
    checking = next((a for a in accounts if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account.")
    return checking


@app.get("/api/drafts")
async def drafts(ticket_id: int | None = None) -> dict[str, Any]:
    """Customer message drafts on the board. They are never sent."""
    return await call_mcp("list_drafts", {"ticket_id": ticket_id})


@app.post("/api/reset")
async def reset() -> dict[str, Any]:
    """Copy campus_customs.db back over the working copy and clear approvals/drafts. Audit trail is kept."""
    _require_idle("reset")
    result = await call_mcp("reset_database")
    AuditTrail(f"reset-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}").log("database_reset", result=result)
    return result


@app.get("/")
async def index() -> dict[str, Any]:
    return {"app": "Campus Customs Ticket Board API", "model": MODEL_NAME, "docs": "/docs"}
