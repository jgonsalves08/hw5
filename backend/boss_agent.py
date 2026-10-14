"""Boss Agent — reads each ticket, routes it to the right agents, and makes the final call.

Prompt: prompts/boss.md. MCP tools: TOOLS_BY_AGENT["boss"] in mcp_client.py.
Can delegate to any other agent through ask_agent (see team.py).
"""

from pydantic_ai import Agent

from config import load_prompt
from mcp_client import toolset_for
from models import TicketDecision
from team import TeamDeps, ask_agent

agent = Agent(
    name="boss",
    instructions=load_prompt("boss"),
    deps_type=TeamDeps,
    output_type=TicketDecision,
    toolsets=[toolset_for("boss")],
    tools=[ask_agent],
    retries=2,
)
