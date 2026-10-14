"""The agent loop and delegation that connect the five agents.

Every agent has the same `ask_agent` tool, so any agent can hand work to any
other (full connectivity). Guardrails on that tool keep the team from looping:
no agent can call one already in its delegation chain, the chain can be at
most MAX_DELEGATION_DEPTH deep, and each ticket has a delegation budget.

`run_agent` drives a PydanticAI agent node-by-node (agent.iter) and appends an
audit event for every loop step: run_start -> (model_request -> model_response
-> tool calls/results)* -> run_end.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import RetryPromptPart, TextPart, ThinkingPart, ToolCallPart, ToolReturnPart, UserPromptPart

from audit import AuditTrail
from config import BOSS_LIMITS, MAX_DELEGATION_DEPTH, MAX_DELEGATIONS_PER_TICKET, SPECIALIST_LIMITS
from mcp_client import TOOLS_BY_AGENT
from models import AGENT_TITLES, AgentKey, Delegation


@dataclass
class TicketBudget:
    """Shared by every agent working one ticket."""

    delegations_used: int = 0
    delegations: list[Delegation] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=lambda: {"requests": 0, "tool_calls": 0,
                                                           "input_tokens": 0, "output_tokens": 0})


@dataclass
class TeamDeps:
    agent: str
    audit: AuditTrail
    model: Any
    budget: TicketBudget
    ticket_id: int | None = None
    depth: int = 0
    parent: str | None = None
    chain: tuple[str, ...] = ()


def get_agent(key: str) -> Agent:
    # Imported here because each agent module imports ask_agent from this one.
    import accounting_agent
    import boss_agent
    import customer_service_agent
    import facilities_agent
    import inventory_agent

    return {
        "boss": boss_agent.agent,
        "inventory": inventory_agent.agent,
        "accounting": accounting_agent.agent,
        "facilities": facilities_agent.agent,
        "customer_service": customer_service_agent.agent,
    }[key]


async def ask_agent(ctx: RunContext[TeamDeps], agent: AgentKey, task: str) -> dict[str, Any]:
    """Delegate a task to another Campus Customs agent and get its report back.

    Args:
        agent: Who to ask: "boss", "inventory", "accounting", "facilities", or "customer_service".
        task: A self-contained task. Include the ticket id and every fact the other agent needs;
            it cannot see your conversation.
    """
    deps = ctx.deps
    budget = deps.budget
    log = dict(agent=deps.agent, ticket_id=deps.ticket_id, depth=deps.depth, parent_agent=deps.parent)

    refusal = None
    if agent == deps.agent:
        refusal = "You cannot delegate to yourself."
    elif agent in deps.chain:
        refusal = f"{agent} is already working on this request higher up the chain {list(deps.chain)}; answer it yourself."
    elif deps.depth + 1 > MAX_DELEGATION_DEPTH:
        refusal = f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached; finish with what you have."
    elif budget.delegations_used >= MAX_DELEGATIONS_PER_TICKET:
        refusal = f"Ticket delegation budget ({MAX_DELEGATIONS_PER_TICKET}) used up; finish with what you have."

    if refusal:
        record = Delegation(from_agent=deps.agent, to_agent=agent, task=task, depth=deps.depth + 1,
                            status="refused", error=refusal)
        budget.delegations.append(record)
        deps.audit.log("delegation_refused", **log, to_agent=agent, task=task, reason=refusal)
        return {"status": "refused", "reason": refusal}

    budget.delegations_used += 1
    deps.audit.log("delegation_start", **log, to_agent=agent, task=task,
                   delegation_number=budget.delegations_used)
    child = replace(deps, agent=agent, depth=deps.depth + 1, parent=deps.agent, chain=deps.chain + (deps.agent,))
    t0 = time.monotonic()
    try:
        report = await run_agent(agent, task, child)
        record = Delegation(from_agent=deps.agent, to_agent=agent, task=task, depth=child.depth,
                            status="done", report=report, duration_ms=int((time.monotonic() - t0) * 1000))
    except Exception as exc:  # one failing agent should not sink the ticket
        record = Delegation(from_agent=deps.agent, to_agent=agent, task=task, depth=child.depth, status="error",
                            error=f"{type(exc).__name__}: {exc}", duration_ms=int((time.monotonic() - t0) * 1000))
    budget.delegations.append(record)
    deps.audit.log("delegation_end", **log, to_agent=agent, status=record.status,
                   report=record.report.model_dump() if record.report else None, error=record.error,
                   duration_ms=record.duration_ms)
    if record.report:
        return {"status": "done", "report": record.report.model_dump()}
    return {"status": "error", "error": record.error}


async def run_agent(key: str, prompt: str, deps: TeamDeps) -> Any:
    """Run one agent's loop step by step, auditing each step. Returns its structured output."""
    agent = get_agent(key)
    limits = BOSS_LIMITS if key == "boss" else SPECIALIST_LIMITS
    log = dict(agent=key, ticket_id=deps.ticket_id, depth=deps.depth, parent_agent=deps.parent)
    t0 = t_req = time.monotonic()
    turn = 0

    deps.audit.log("run_start", **log, title=AGENT_TITLES[key], prompt=prompt,
                   mcp_tools=sorted(TOOLS_BY_AGENT[key]), chain=list(deps.chain),
                   limits={"request_limit": limits.request_limit, "tool_calls_limit": limits.tool_calls_limit,
                           "total_tokens_limit": limits.total_tokens_limit})
    try:
        async with agent.iter(prompt, deps=deps, model=deps.model, usage_limits=limits) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    turn += 1
                    t_req = time.monotonic()
                    parts = []
                    for p in node.request.parts:
                        if isinstance(p, ToolReturnPart):
                            parts.append({"type": "tool_return", "tool": p.tool_name, "tool_call_id": p.tool_call_id})
                        elif isinstance(p, RetryPromptPart):
                            parts.append({"type": "retry", "tool": p.tool_name, "content": str(p.content)})
                        elif isinstance(p, UserPromptPart):
                            parts.append({"type": "user_prompt"})
                        else:
                            parts.append({"type": type(p).__name__})
                    deps.audit.log("model_request", **log, turn=turn, parts=parts)
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    deps.audit.log(
                        "model_response", **log, turn=turn,
                        duration_ms=int((time.monotonic() - t_req) * 1000),
                        model=resp.model_name, finish_reason=resp.finish_reason,
                        input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                        tool_calls=[{"tool": p.tool_name, "args": p.args_as_dict(), "tool_call_id": p.tool_call_id}
                                    for p in resp.parts if isinstance(p, ToolCallPart)],
                        text="".join(p.content for p in resp.parts if isinstance(p, TextPart)),
                        thinking_chars=sum(len(p.content) for p in resp.parts if isinstance(p, ThinkingPart)),
                    )
            result = run.result
    except BaseException as exc:  # includes cancellation by the ticket timeout
        deps.audit.log("run_error", **log, turns=turn, error=f"{type(exc).__name__}: {exc}",
                       duration_ms=int((time.monotonic() - t0) * 1000))
        raise

    usage = result.usage
    for k in deps.budget.usage:
        deps.budget.usage[k] += getattr(usage, k) or 0
    deps.audit.log("run_end", **log, turns=turn, requests=usage.requests, tool_calls=usage.tool_calls,
                   input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                   duration_ms=int((time.monotonic() - t0) * 1000), output=result.output.model_dump())
    return result.output
