"""Connection to the campus-customs MCP server, the team's only source of shop facts.

One stdio MCP connection is shared by every agent. Each agent sees a filtered
view holding only the tools its role needs (least privilege). Every call also
passes through `_process_tool_call`, which:
  - re-checks the allowlist (defense in depth),
  - stamps prepared_by / drafted_by with the real agent so no agent can sign
    as another, and fills in the ticket being worked,
  - writes the tool call and its result to the audit trail.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset, StdioTransport

from config import MCP_SERVER_PATH

TOOLS_BY_AGENT: dict[str, frozenset[str]] = {
    "boss": frozenset({
        "get_desk_today", "list_tickets", "get_ticket", "list_approvals", "list_drafts", "update_ticket_status",
    }),
    "inventory": frozenset({
        "get_desk_today", "get_ticket", "check_inventory", "check_price", "list_vendors", "list_invoices",
    }),
    "accounting": frozenset({
        "get_desk_today", "get_ticket", "check_overdue", "check_price", "get_cash_balance", "list_invoices",
        "list_obligations", "list_payments", "list_vendors", "list_approvals", "prepare_payment",
        "prepare_purchase_order",
    }),
    "facilities": frozenset({
        "get_desk_today", "get_ticket", "check_overdue", "list_leases", "list_payments", "get_cash_balance",
    }),
    "customer_service": frozenset({
        "get_desk_today", "get_ticket", "check_inventory", "list_drafts", "draft_customer_message",
    }),
}

# Tools only a person (or the runner, for reset) may call. No agent ever gets these.
HUMAN_ONLY_TOOLS = frozenset({"pay", "approve_purchase_order", "reject_request", "reset_database"})
assert not any(tools & HUMAN_ONLY_TOOLS for tools in TOOLS_BY_AGENT.values())

SIGNER_ARG = {"prepare_payment": "prepared_by", "prepare_purchase_order": "prepared_by",
              "draft_customer_message": "drafted_by"}
TICKET_ARG_TOOLS = {"prepare_payment", "prepare_purchase_order"}


def _as_jsonable(result: Any) -> Any:
    try:
        json.dumps(result)
        return result
    except TypeError:
        return str(result)


async def _process_tool_call(ctx: RunContext[Any], call_tool: CallToolFunc, name: str, args: dict[str, Any]) -> Any:
    deps = ctx.deps
    agent = deps.agent
    if name not in TOOLS_BY_AGENT[agent]:
        deps.audit.log("tool_refused", agent=agent, ticket_id=deps.ticket_id, depth=deps.depth,
                       parent_agent=deps.parent, tool=name, args=args)
        return {"error": f"{agent} is not allowed to call {name}."}

    args = dict(args)
    if name in SIGNER_ARG:
        args[SIGNER_ARG[name]] = agent
    if name in TICKET_ARG_TOOLS and args.get("ticket_id") is None:
        args["ticket_id"] = deps.ticket_id

    deps.audit.log("tool_call", agent=agent, ticket_id=deps.ticket_id, depth=deps.depth,
                   parent_agent=deps.parent, tool=name, args=args, tool_call_id=ctx.tool_call_id)
    try:
        result = await call_tool(name, args)
    except Exception as exc:
        deps.audit.log("tool_error", agent=agent, ticket_id=deps.ticket_id, depth=deps.depth,
                       parent_agent=deps.parent, tool=name, error=f"{type(exc).__name__}: {exc}")
        raise
    deps.audit.log("tool_result", agent=agent, ticket_id=deps.ticket_id, depth=deps.depth,
                   parent_agent=deps.parent, tool=name, tool_call_id=ctx.tool_call_id,
                   result=json.dumps(_as_jsonable(result), default=str))
    return result


campus_customs = MCPToolset(
    StdioTransport(command=sys.executable, args=[str(MCP_SERVER_PATH)]),
    id="campus-customs",
    process_tool_call=_process_tool_call,
    tool_error_behavior="retry",
)


def toolset_for(agent: str):
    """The MCP tools one agent may see."""
    allowed = TOOLS_BY_AGENT[agent]
    return campus_customs.filtered(lambda ctx, tool_def: tool_def.name in allowed)


async def call_mcp(name: str, args: dict[str, Any] | None = None) -> Any:
    """Direct call for the runner and the human approval CLI (no agent involved)."""
    return await campus_customs.direct_call_tool(name, args or {})
