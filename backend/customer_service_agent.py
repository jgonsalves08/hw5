"""Customer Service Agent — drafts messages to customers. Drafts stay on the board and are never sent.

Prompt: prompts/customer_service.md. MCP tools: TOOLS_BY_AGENT["customer_service"] in mcp_client.py.
Can delegate to any other agent through ask_agent (see team.py).
"""

from pydantic_ai import Agent

from config import load_prompt
from mcp_client import toolset_for
from models import AgentReport
from team import TeamDeps, ask_agent

agent = Agent(
    name="customer_service",
    instructions=load_prompt("customer_service"),
    deps_type=TeamDeps,
    output_type=AgentReport,
    toolsets=[toolset_for("customer_service")],
    tools=[ask_agent],
    retries=2,
)
