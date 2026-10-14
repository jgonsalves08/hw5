"""Facilities Agent — handles the shop space: leases, rent notices, and rent due dates.

Prompt: prompts/facilities.md. MCP tools: TOOLS_BY_AGENT["facilities"] in mcp_client.py.
Can delegate to any other agent through ask_agent (see team.py).
"""

from pydantic_ai import Agent

from config import load_prompt
from mcp_client import toolset_for
from models import AgentReport
from team import TeamDeps, ask_agent

agent = Agent(
    name="facilities",
    instructions=load_prompt("facilities"),
    deps_type=TeamDeps,
    output_type=AgentReport,
    toolsets=[toolset_for("facilities")],
    tools=[ask_agent],
    retries=2,
)
