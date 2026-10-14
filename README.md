# Campus Customs — Agent Ticket Desk (HW5)

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) that works the Campus Customs ticket queue.

- **Agents:** PydanticAI, calling `gpt-6-luna` through Portkey.
- **Shop facts:** come **only** from a FastMCP server over `data/campus_customs_new.db`.
- **Board:** a FastAPI backend serves a React board where you watch the agents work and **approve payments yourself**. Agents can only queue money; a person has to click Approve.

```
React board (frontend/, :5173) → FastAPI (backend/main.py, :8000) → 5 agents (backend/*_agent.py)
                                                                   → MCP server (mcp_server/server.py) → data/campus_customs_new.db
every agent step → output/audit_trail.json
```

## Project layout

| Path | What it is |
|---|---|
| `data/campus_customs.db` | The **original** database. Never written to. |
| `data/campus_customs_new.db` | The **working copy** the agents read and write. It is committed in its post-run state (checking $160.00, all three tickets resolved). |
| `mcp_server/server.py` | FastMCP server with 22 tools (see `mcp_server/README.md`) |
| `backend/` | FastAPI app (`main.py`), the five agents, prompts (`prompts/`), data types (`models.py`) |
| `frontend/` | React + Vite + TypeScript board |
| `output/` | Harness, audit trail, desk tickets, design notes, resolved results, GitHub URL |
| `.mcp.json` | Connects Claude Code (or any MCP client) to the server |

## 1. One-time setup

You need Python 3.11+ and Node 18+. From the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then put your real PORTKEY_API_KEY in .env
cd frontend && npm install && cd ..
```

`.env` is git-ignored. Only `.env.example` (with a placeholder) is committed.

## 2. Copy the original database to the working copy (clean run)

The working copy in the repo holds the results of the graded run. To start from the original data instead:

```bash
cp data/campus_customs.db data/campus_customs_new.db
echo "[]" > output/approvals.json
echo "[]" > output/drafts.json
```

This puts checking back to $3,400.00, all tickets back to `open`, invoice 501 back to unpaid, and the payments table back to empty. It also clears the approval queue and drafts. The **Reset desk** button (step 6) does the same thing for you while the app is running.

## 3. Start the MCP server

**You don't have to start it by hand for the app.** The FastAPI backend launches `mcp_server/server.py` itself over stdio when it starts. To run or inspect it on its own:

```bash
.venv/bin/python mcp_server/server.py          # stdio (what the backend and .mcp.json use)
.venv/bin/python mcp_server/server.py --http   # HTTP at http://127.0.0.1:8002/mcp
```

Claude Code picks it up automatically from `.mcp.json` when you open this folder.

## 4. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

API docs are at http://127.0.0.1:8000/docs. Leave this terminal running. Don't edit backend files during a run: `--reload` restarts the server and stops the run.

## 5. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. Then:
1. **Pick a ticket** on the right.
2. Click the green **▶ Send the team in** button.
3. Watch each agent work, including the numbered hand-off arrows.
4. When the ticket is resolved, type your name under **Needs your OK** and click **Approve** twice to pay. The Checking Account balance drops right away.

## 6. Reset the working database before a full three-ticket run

Always reset first, so the run starts from the original values ($3,400.00 in checking). Use any one of these:

- **On the board:** click **Reset desk** (top right), then click it again to confirm.
- **From a terminal, while the backend is running:**
  ```bash
  curl -X POST http://localhost:8000/api/reset
  ```
- **Without the board:** this resets the database, then runs tickets 101, 102 and 103 in order. Approve the queued payments afterwards with the second command.
  ```bash
  .venv/bin/python backend/run_tickets.py
  .venv/bin/python backend/approve.py
  ```

Each reset copies `campus_customs.db` over `campus_customs_new.db` and clears the approval queue and drafts. The audit trail is never cleared, so earlier runs stay on record.

## Safety in one paragraph

No agent can pay anything. The `pay` tool is only reachable through the human Approve route or `approve.py`. It refuses agent names, double payments and anything that would make a balance negative. Cash only goes out, and nobody is emailed or called: customer messages stay as drafts on the board. The full guardrails and token limits are in `output/harness.md`.

## Where the results are

| File | What it is |
|---|---|
| `output/harness.md` | Tables, MCP tools, agents, API routes, dashboard, safety rules |
| `output/desk_tickets.html` | Expected vs. Actual for each ticket, plus the Cash ledger and the Reflection |
| `output/resolved_tickets.json` | Per-ticket final status, outcome, agent contributions, human approvals |
| `output/resolved_board.html` | Screenshots of the board for each resolved ticket |
| `output/audit_trail.json` | Every agent-loop step, tool call, hand-off and human decision (append-only) |
| `output/design.md` | Dashboard design choices |
| `output/mcp_smoke.json` | MCP tool smoke tests |
| `AI_prompts.md` | The prompts used for each problem |
