"""Accounting Agent — watches cash and invoices, checks margins, and queues payments and purchase orders for human approval.

Prompt: prompts/accounting.md. MCP tools: TOOLS_BY_AGENT["accounting"] in mcp_client.py.
Can delegate to any other agent through ask_agent (see team.py).
"""

from pydantic_ai import Agent

from config import load_prompt
from mcp_client import toolset_for
from models import AgentReport
from team import TeamDeps, ask_agent

agent = Agent(
    name="accounting",
    instructions=load_prompt("accounting"),
    deps_type=TeamDeps,
    output_type=AgentReport,
    toolsets=[toolset_for("accounting")],
    tools=[ask_agent],
    retries=2,
)
