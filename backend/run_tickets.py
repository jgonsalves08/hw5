"""Full team run over the open tickets.

    .venv/bin/python backend/run_tickets.py              # reset DB, then work every open ticket
    .venv/bin/python backend/run_tickets.py --ticket 102 # only ticket 102 (still resets first)
    .venv/bin/python backend/run_tickets.py --no-reset   # keep the current DB state

Steps: reset_database over MCP (so the run starts from the original values),
then the Boss Agent works each open ticket in order, delegating to the other
agents. Tickets run one after another, so later tickets see the payments
earlier ones queued. Nothing is paid here; payments wait for backend/approve.py.
The run summary is saved to output/latest_run.json for the board, and every
step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone

from audit import AuditTrail
from config import LATEST_RUN_PATH, MODEL_NAME, TICKET_TIMEOUT_SECONDS, build_model
from mcp_client import call_mcp, campus_customs
from models import TeamRun, TicketResult
from team import TeamDeps, TicketBudget, run_agent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id() -> str:
    return f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"


async def run_team(reset: bool = True, ticket_ids: list[int] | None = None, run_id: str | None = None) -> TeamRun:
    """Work the open tickets, or exactly `ticket_ids` (whatever their status) if given."""
    run_id = run_id or new_run_id()
    audit = AuditTrail(run_id)
    model = build_model()
    team = TeamRun(run_id=run_id, started_at=_now(), model=MODEL_NAME)

    async with campus_customs:
        if reset:
            team.reset = await call_mcp("reset_database")
            audit.log("database_reset", result=team.reset)
        if ticket_ids:
            found = [await call_mcp("get_ticket", {"ticket_id": i}) for i in ticket_ids]
            tickets = [f["ticket"] for f in found if "ticket" in f]
        else:
            tickets = (await call_mcp("list_tickets", {"status": "open"}))["tickets"]
        audit.log("team_run_start", model=MODEL_NAME, reset=reset, ticket_ids=[t["id"] for t in tickets])

        for ticket in tickets:
            tid = ticket["id"]
            budget = TicketBudget()
            deps = TeamDeps(agent="boss", audit=audit, model=model, budget=budget, ticket_id=tid)
            audit.log("ticket_start", agent="boss", ticket_id=tid, ticket=ticket)
            result = TicketResult(ticket_id=tid)
            try:
                result.decision = await asyncio.wait_for(
                    run_agent("boss", f"Work ticket {tid} ({ticket['type']}: {ticket['subject']}).", deps),
                    timeout=TICKET_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                result.error = f"Timed out after {TICKET_TIMEOUT_SECONDS}s; ticket left for a human."
            except Exception as exc:
                result.error = f"{type(exc).__name__}: {exc}"
            result.delegations, result.usage = budget.delegations, budget.usage
            audit.log("ticket_end", agent="boss", ticket_id=tid, error=result.error, usage=result.usage,
                      decision=result.decision.model_dump() if result.decision else None)
            team.tickets.append(result)

        team.pending_approvals = (await call_mcp("list_approvals", {"status": "pending"}))["approvals"]
        team.drafts = (await call_mcp("list_drafts"))["drafts"]

    team.finished_at = _now()
    team.usage = {k: sum(t.usage.get(k, 0) for t in team.tickets)
                  for k in ("requests", "tool_calls", "input_tokens", "output_tokens")}
    audit.log("team_run_end", usage=team.usage, pending_approvals=[a["id"] for a in team.pending_approvals],
              drafts=[d["id"] for d in team.drafts])
    LATEST_RUN_PATH.write_text(json.dumps(team.model_dump(mode="json"), indent=2))
    return team


def _print_summary(team: TeamRun) -> None:
    print(f"\nRun {team.run_id}  model={team.model}  usage={team.usage}")
    for t in team.tickets:
        print(f"\n=== Ticket {t.ticket_id} ===")
        if t.error:
            print("ERROR:", t.error)
        if t.decision:
            d = t.decision
            print(f"status: {d.ticket_status}   agents: {', '.join(d.agents_consulted)}")
            print("decision:", d.decision)
            for step in d.next_steps_for_human:
                print("  -", step)
        for g in t.delegations:
            print(f"  [{g.status}] {g.from_agent} -> {g.to_agent}")
    print("\nWaiting for human approval:")
    for a in team.pending_approvals:
        what = f"${a['amount']:.2f} to {a['payee']}" if a["type"] == "payment" else \
            f"{a['qty']} x {a['sku']} {a['size']} from {a['vendor']} (~${a['estimated_cost']:.2f})"
        print(f"  {a['id']}: {what}")
    print("\nDrafts on the board (not sent):", ", ".join(d["id"] for d in team.drafts) or "none")
    print("\nReview approvals with:  .venv/bin/python backend/approve.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team on open tickets.")
    parser.add_argument("--ticket", type=int, action="append", help="Only work this ticket id (repeatable).")
    parser.add_argument("--no-reset", action="store_true", help="Do not reset the database first.")
    args = parser.parse_args()
    _print_summary(asyncio.run(run_team(reset=not args.no_reset, ticket_ids=args.ticket)))


if __name__ == "__main__":
    main()
