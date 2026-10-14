"""Inventory Agent — checks stock by SKU and size, spots shortfalls, and finds a vendor that can restock.

Prompt: prompts/inventory.md. MCP tools: TOOLS_BY_AGENT["inventory"] in mcp_client.py.
Can delegate to any other agent through ask_agent (see team.py).
"""

from pydantic_ai import Agent

from config import load_prompt
from mcp_client import toolset_for
from models import AgentReport
from team import TeamDeps, ask_agent

agent = Agent(
    name="inventory",
    instructions=load_prompt("inventory"),
    deps_type=TeamDeps,
    output_type=AgentReport,
    toolsets=[toolset_for("inventory")],
    tools=[ask_agent],
    retries=2,
)
