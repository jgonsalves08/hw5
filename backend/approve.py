"""Human approval desk: the ONLY way a payment or purchase order gets approved.

    .venv/bin/python backend/approve.py          # review each pending request
    .venv/bin/python backend/approve.py --list   # just list them

A person types their name (saved as payments.approved_by) and approves or
rejects each request. Payments go through the MCP `pay` tool, which re-checks
the bill and the cash and refuses if the balance would go negative. Approving a
purchase order only marks it approved; nothing is sent to the vendor.
No agent can reach this file's tools.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from audit import AuditTrail
from mcp_client import call_mcp, campus_customs


def _describe(a: dict) -> str:
    if a["type"] == "payment":
        return (f"{a['id']}  PAY ${a['amount']:.2f} to {a['payee']} ({a['kind']} {a['ref_id']}, due {a['due_date']}) "
                f"from {a['account']}; balance after ≈ ${a['balance_after_if_approved']:.2f}\n"
                f"      ticket {a['ticket_id']} · prepared by {a['prepared_by']}: {a['reason']}")
    blocked = " — vendor BLOCKED until open invoice is paid" if not a["will_ship"] else ""
    return (f"{a['id']}  PO {a['qty']} x {a['sku']} {a['size']} from {a['vendor']}, ~${a['estimated_cost']:.2f}, "
            f"ETA {a['eta_if_approved_today']}{blocked}\n"
            f"      ticket {a['ticket_id']} · prepared by {a['prepared_by']}: {a['reason']}")


async def review(list_only: bool) -> None:
    audit = AuditTrail(f"human-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    async with campus_customs:
        pending = (await call_mcp("list_approvals", {"status": "pending"}))["approvals"]
        if not pending:
            print("Nothing is waiting for approval.")
            return
        for a in pending:
            print(_describe(a))
        if list_only:
            return

        name = input("\nYour name (recorded as approved_by): ").strip()
        if not name:
            print("A name is required. Nothing approved.")
            return
        for a in pending:
            print("\n" + _describe(a))
            choice = input("  [a]pprove / [r]eject / [s]kip? ").strip().lower()[:1]
            if choice == "a":
                tool = "pay" if a["type"] == "payment" else "approve_purchase_order"
                result = await call_mcp(tool, {"approval_id": a["id"], "approved_by": name})
            elif choice == "r":
                reason = input("  reason: ").strip()
                tool = "reject_request"
                result = await call_mcp(tool, {"approval_id": a["id"], "rejected_by": name, "reason": reason})
            else:
                print("  skipped")
                continue
            audit.log("human_decision", agent=None, ticket_id=a.get("ticket_id"), human=name, approval_id=a["id"],
                      tool=tool, result=result)
            if result.get("error"):
                print("  REFUSED:", result["error"])
            elif result.get("paid"):
                print(f"  paid (payment #{result['payment_id']}); {result['account']} balance now "
                      f"${result['balance_after']:.2f}")
            else:
                print("  done:", result.get("message") or f"{a['id']} rejected")


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve or reject queued payments and purchase orders.")
    parser.add_argument("--list", action="store_true", help="List pending requests without deciding.")
    asyncio.run(review(parser.parse_args().list))


if __name__ == "__main__":
    main()
