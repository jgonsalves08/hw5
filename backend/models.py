"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentKey = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_on_approval", "resolved"]

AGENT_TITLES: dict[str, str] = {
    "boss": "Boss Agent",
    "inventory": "Inventory Agent",
    "accounting": "Accounting Agent",
    "facilities": "Facilities Agent",
    "customer_service": "Customer Service Agent",
}


class AgentReport(BaseModel):
    """What a specialist agent hands back to whoever delegated to it."""

    agent: AgentKey
    summary: str = Field(description="Two or three sentences answering the task.")
    facts: list[str] = Field(default_factory=list, description="Shop facts used, each with the MCP tool it came from.")
    actions_taken: list[str] = Field(default_factory=list, description="Write tools called and what they did.")
    approval_ids: list[str] = Field(default_factory=list, description="IDs of payments/POs queued for human approval.")
    draft_ids: list[str] = Field(default_factory=list, description="IDs of message drafts saved to the board.")
    recommendations: list[str] = Field(default_factory=list)
    needs_human: bool = Field(default=False, description="True if a person must approve or decide something.")


class TicketDecision(BaseModel):
    """The Boss Agent's final call on one ticket."""

    ticket_id: int
    agents_consulted: list[AgentKey] = Field(default_factory=list)
    decision: str = Field(description="The final decision in plain language.")
    ticket_status: TicketStatus
    approval_ids: list[str] = Field(default_factory=list)
    draft_ids: list[str] = Field(default_factory=list)
    next_steps_for_human: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class Delegation(BaseModel):
    """One hand-off from one agent to another."""

    from_agent: AgentKey
    to_agent: AgentKey
    task: str
    depth: int
    status: Literal["done", "refused", "error"]
    report: AgentReport | None = None
    error: str | None = None
    duration_ms: int = 0


class AuditEvent(BaseModel):
    """One line in output/audit_trail.json."""

    run_id: str
    seq: int
    ts: str
    step: str
    agent: str | None = None
    ticket_id: int | None = None
    depth: int | None = None
    parent_agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class TicketResult(BaseModel):
    ticket_id: int
    decision: TicketDecision | None = None
    delegations: list[Delegation] = Field(default_factory=list)
    error: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)


class TeamRun(BaseModel):
    """Everything one full run produced; saved to output/latest_run.json for the board."""

    run_id: str
    started_at: str
    finished_at: str | None = None
    model: str
    reset: dict[str, Any] | None = None
    tickets: list[TicketResult] = Field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    drafts: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
