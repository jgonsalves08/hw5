"""Model, paths, and safety limits for the Campus Customs agent team.

Every agent calls gpt-6-luna through the Portkey gateway with PORTKEY_API_KEY,
loaded from HW5/.env if present, otherwise the course-level AI Foundations/.env.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
OUTPUT_DIR = ROOT / "output"
AUDIT_TRAIL_PATH = OUTPUT_DIR / "audit_trail.json"
LATEST_RUN_PATH = OUTPUT_DIR / "latest_run.json"
MCP_SERVER_PATH = ROOT / "mcp_server" / "server.py"

load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT.parent / ".env", override=False)

# The only model any agent may use. Not read from the environment on purpose.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---------- Token and loop limits ----------
# Each agent run is capped by PydanticAI UsageLimits; delegation is capped by
# depth and by a per-ticket budget so agents cannot ping-pong forever.
BOSS_LIMITS = UsageLimits(request_limit=12, tool_calls_limit=20, total_tokens_limit=150_000)
SPECIALIST_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=12, total_tokens_limit=80_000)
MAX_DELEGATION_DEPTH = 2  # boss (0) -> specialist (1) -> specialist (2); depth 2 cannot delegate
MAX_DELEGATIONS_PER_TICKET = 8
TICKET_TIMEOUT_SECONDS = 480
MODEL_REQUEST_TIMEOUT_SECONDS = 30  # normal calls take <5s; a stalled call is dropped and retried
MODEL_MAX_RETRIES = 3
AUDIT_TEXT_LIMIT = 4_000  # chars kept per prompt / tool result / model text in the audit trail


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Put it in HW5/.env or the AI Foundations/.env.")
    return key


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey (OpenAI Responses API, which supports tools with reasoning)."""
    client = AsyncOpenAI(api_key=require_api_key(), base_url=PORTKEY_BASE_URL,
                         timeout=MODEL_REQUEST_TIMEOUT_SECONDS, max_retries=MODEL_MAX_RETRIES)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
