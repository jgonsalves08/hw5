# Campus Customs — Agent Harness

Working database: `data/campus_customs_new.db` (copy of `data/campus_customs.db`; the original stays untouched).

**How the pieces fit**

```
React board (frontend/, :5173)  →  FastAPI routes (backend/main.py, :8000)
                                     → five PydanticAI agents (backend/*_agent.py, gpt-6-luna via Portkey)
                                     → campus-customs MCP server (mcp_server/server.py)
                                     → data/campus_customs_new.db
Every agent step → output/audit_trail.json (append-only)
```

**Sections:** database tables · open tickets · MCP tools · agent team · safety · backend routes · dashboard · output files

**Run it**
1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then put `PORTKEY_API_KEY` in `.env` (see `.env.example`).
2. Backend: `cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000`
3. Board: `cd frontend && npm install && npm run dev`, then open `http://localhost:5173`.
4. Optional, without the board: `.venv/bin/python backend/run_tickets.py` (resets the database, then runs every open ticket) and `.venv/bin/python backend/approve.py` (human approvals).

---

## Database tables

### `desk`
| Field | Type | Notes |
|---|---|---|
| date_today | TEXT | The business's current date (`2026-08-31`) |
| notes | TEXT | Free-form desk notes |

**Why it matters:** It tells the agents what "today" is, so they can judge what is overdue or due soon instead of using the real-world clock.

### `inventory`
| Field | Type | Notes |
|---|---|---|
| sku | TEXT | Product code (PK with size) |
| name | TEXT | Product name |
| size | TEXT | S / M / L / XL / OS |
| qty | INTEGER | Units on hand |
| location | TEXT | Aisle in the shop |

**Why it matters:** Agents check this before promising an order, because they need to know whether the SKU and size are actually in stock.

### `pricing`
| Field | Type | Notes |
|---|---|---|
| sku | TEXT | Product code (PK) |
| unit_cost | REAL | What the shop pays per unit |
| list_price | REAL | Standard selling price |

**Why it matters:** Agents use it to quote prices and to find the floor for a discount, since anything below `unit_cost` loses money.

### `vendors`
| Field | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| name | TEXT | Vendor name |
| specialty | TEXT | What they supply |
| lead_days | INTEGER | Days to deliver |

**Why it matters:** Agents use it to decide who to reorder from and how long restocking will take.

### `leases`
| Field | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| space_name | TEXT | Rented space |
| landlord | TEXT | Who is owed rent |
| monthly_rent | REAL | Rent amount |
| next_due | TEXT | Next rent due date |
| notes | TEXT | Free-form notes |

**Why it matters:** It is the source of truth for rent owed and when it's due. Agents should check it to confirm a rent notice is real before any money moves.

### `cash_accounts`
| Field | Type | Notes |
|---|---|---|
| name | TEXT | Account name (PK) |
| balance | REAL | Current balance |
| date | TEXT | As-of date for the balance |

**Why it matters:** It is the hard limit on what the shop can pay. Agents must check the balance before paying anything and account for every obligation competing for the same cash.

### `payments`
| Field | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| kind | TEXT | What was paid (e.g., rent, invoice) |
| ref_id | INTEGER | ID of the lease or invoice paid |
| amount | REAL | Amount paid |
| account | TEXT | Cash account it came from |
| paid_at | TEXT | Timestamp |
| approved_by | TEXT | Who approved it |

**Why it matters:** It is the audit trail for money leaving the shop. Agents write here only after a payment is approved, and `approved_by` records who signed off. The table is currently empty.

### `invoices`
| Field | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| vendor_id | INTEGER | FK → `vendors.id` |
| amount | REAL | Amount owed |
| due_date | TEXT | Due date |
| status | TEXT | open / paid |
| description | TEXT | What the invoice covers |

**Why it matters:** It lists what the shop owes vendors. Agents use it to spot overdue bills and to link stock problems to replenishment that is already in progress.

### `tickets`
| Field | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| type | TEXT | customer_order / rent_notice / price_override |
| requester | TEXT | Who asked |
| subject | TEXT | Short title |
| sku | TEXT | Related product (→ `inventory`, `pricing`) |
| size | TEXT | Related size |
| qty | INTEGER | Quantity requested |
| lease_id | INTEGER | FK → `leases.id` |
| invoice_id | INTEGER | FK → `invoices.id` |
| status | TEXT | open / in_progress / waiting_on_approval / resolved |
| notes | TEXT | Request details |
| created_at | TEXT | Timestamp |

**Why it matters:** This is the agents' work queue. Each ticket is a request to route to the right agent, and its foreign keys point to the other tables needed to resolve it.

---

## Open tickets and how they connect

| Ticket | Request | Linked tables | Key facts |
|---|---|---|---|
| **101** customer_order (Tauhid Zaman) | 1 × Classic Bulldog Tee, size S | `inventory`, `pricing`, `invoices` (501) → `vendors` (1) | Tee S has **0 in stock**. Invoice 501 is an $840 rush reprint of that tee from Bulldog Print Co (5-day lead time). It was due 2026-08-28, so it is **3 days overdue** and still open. |
| **102** rent_notice (Elm City Properties) | Shop rent due in 2 days | `leases` (1), `cash_accounts`, `payments` | Rent of $2,400 is due 2026-09-02, which matches the lease. Checking has **$3,400**. |
| **103** price_override (Yale AI Club) | 20 hoodies, size M, bulk discount | `inventory`, `pricing`, `vendors` | Only **8 Hoodie M** are in stock (32 across all sizes). List price is $58 and unit cost is $22, so any discount must stay above $22. Restocking from Bulldog Print Co takes 5 days. |

**Cross-ticket tension:** Rent ($2,400) plus the overdue invoice ($840) comes to $3,240. That leaves only **$160** in checking, so agents need to prioritize payments and get human approval (`payments.approved_by`) before moving money.

---

## MCP tools (Problem 3)

Server: `mcp_server/server.py` (FastMCP, read-only connection to `data/campus_customs_new.db`).

### 1. `check_inventory(sku, size, qty_requested)`
- **Reads:** `inventory`
- **Unlocks tickets:** **101** and **103**
  - **101** (1 × Classic Bulldog Tee, size S): Before the agent can promise Tauhid a tee, it has to confirm the shop carries CC-TEE-WHITE in size S and see that it's actually at 0 on hand. That turns the ticket from "ship it" into "backorder, or offer another size," and it explains why reprint invoice 501 exists.
  - **103** (20 × Basic Hoodie, size M): A discount is meaningless if we can't deliver the goods. The tool shows only 8 size M hoodies on hand (a shortfall of 12), so the agent knows the club order needs a partial shipment, a reprint, or a size substitution before any price is agreed.

### 2. `check_overdue(ticket_id)`
- **Reads:** `tickets`, `desk`, `leases`, `invoices` (joined to `vendors`)
- **Unlocks tickets:** **102** and **101**
  - **102** (rent notice from Elm City Properties): A rent notice that arrives by email shouldn't be paid on trust, so this tool checks the claim against the lease's real `next_due` date and the shop's `desk.date_today`. It confirms rent is due in 2 days and not yet late, which lets the agent schedule the payment instead of rushing it.
  - **101** (Bulldog tee order): The ticket links to invoice 501, the $840 rush reprint of the out-of-stock tee. The tool shows that invoice is 3 days overdue, which tells the agent the restock may be held up until Bulldog Print Co is paid and puts that bill in competition with rent for the same $3,400.
  - **103** has no lease or invoice, so the tool correctly reports that it can't be overdue.

### 3. `check_price(sku, proposed_unit_price, qty)`
- **Reads:** `pricing`
- **Unlocks tickets:** **103** and **101**
  - **103** (Yale AI Club bulk discount): Deciding on a bulk discount means knowing the hoodie's $22 unit cost as well as its $58 list price. This tool calculates the break-even floor and the profit at any proposed price, so the agent can make a counteroffer that wins the order without selling below cost.
  - **101** (Bulldog tee order): It gives the agent the tee's $28 list price to quote Tauhid. It also shows the $8 unit cost, which puts the single-tee sale in perspective next to the $840 rush reprint behind it.

---

## Agent team (Problem 5)

Built with PydanticAI (`pydantic-ai-slim[openai,mcp]`). Every agent uses **`gpt-6-luna` through Portkey** (OpenAI Responses API) with `PORTKEY_API_KEY` from `.env`. Shop facts come **only** from the campus-customs MCP server over `data/campus_customs_new.db`.

| Agent | File / prompt | Role | MCP tools it can call | Returns |
|---|---|---|---|---|
| **Boss** | `backend/boss_agent.py` / `prompts/boss.md` | Reads each ticket, decides which agents work on it, collects their reports, makes the final decision, and sets the ticket status (`resolved` once the team's work is done; queued payments stay in the approval queue). | `get_ticket`, `list_tickets`, `get_desk_today`, `list_approvals`, `list_drafts`, `update_ticket_status` | `TicketDecision` |
| **Inventory** | `backend/inventory_agent.py` / `prompts/inventory.md` | Checks stock by SKU and size, spots shortfalls, checks whether an open invoice already covers the restock, and picks the vendor that can restock (with lead time, ETA, and whether it is blocked). | `check_inventory`, `check_price`, `list_vendors`, `list_invoices`, `get_ticket`, `get_desk_today` | `AgentReport` |
| **Accounting** | `backend/accounting_agent.py` / `prompts/accounting.md` | Watches cash and invoices, checks margins and discounts, and **queues** payments and purchase orders for human approval. | `list_obligations`, `get_cash_balance`, `list_invoices`, `list_payments`, `list_vendors`, `list_approvals`, `check_price`, `check_overdue`, `prepare_payment`, `prepare_purchase_order`, `get_ticket`, `get_desk_today` | `AgentReport` |
| **Facilities** | `backend/facilities_agent.py` / `prompts/facilities.md` | Handles the shop space. It verifies rent notices against the lease (landlord, amount, due date), checks they are not already paid, and hands verified rent to Accounting. | `list_leases`, `check_overdue`, `list_payments`, `get_cash_balance`, `get_ticket`, `get_desk_today` | `AgentReport` |
| **Customer Service** | `backend/customer_service_agent.py` / `prompts/customer_service.md` | Drafts customer messages. Drafts are saved to the board and never sent. It shares no internal money details. | `draft_customer_message`, `list_drafts`, `check_inventory`, `get_ticket`, `get_desk_today` | `AgentReport` |

**Delegation (full connectivity):** Every agent has the same `ask_agent(agent, task)` tool (`backend/team.py`), so any agent can hand work to any other. For example, Facilities hands verified rent straight to Accounting.

**Agent loop:** `run_agent` drives each agent with `agent.iter()`: model request → model response → MCP and `ask_agent` tool calls → … → structured output. `backend/run_tickets.py` resets the database over MCP, then has the Boss work each open ticket in order.

**Data types:** `backend/models.py` defines `AgentReport`, `TicketDecision`, `Delegation`, `AuditEvent`, `TicketResult`, and `TeamRun`.

**Audit trail:** Every loop step is **appended** to `output/audit_trail.json` and never wiped. The steps are:
- `run_start` (prompt, allowed tools, limits)
- `model_request`
- `model_response` (tool calls and arguments, text, tokens, latency)
- `tool_call` / `tool_result`
- `delegation_start` / `delegation_end` / `delegation_refused`
- `run_end` (usage and structured output) or `run_error`
- the ticket- and run-level events
- `human_decision` (from `approve.py`)

Each event carries `run_id`, `seq`, timestamp, agent, ticket, depth, and parent agent.

---

## All MCP tools (Problem 3 + Problem 5)

| Tool | Tables used | Who can call it | Added in |
|---|---|---|---|
| `check_inventory` | `inventory` | Inventory, Customer Service | P3 |
| `check_overdue` | `tickets`, `desk`, `leases`, `invoices`, `vendors` | Accounting, Facilities | P3 |
| `check_price` | `pricing` | Inventory, Accounting | P3 |
| `get_desk_today` | `desk` | all agents | P5 |
| `list_tickets` | `tickets` | Boss | P5 |
| `get_ticket` | `tickets`, `leases`, `invoices`, `vendors` | all agents | P5 |
| `get_cash_balance` | `cash_accounts` (+ approval queue) | Accounting, Facilities | P5 |
| `list_invoices` | `invoices`, `vendors`, `desk` | Inventory, Accounting | P5 |
| `list_vendors` | `vendors`, `invoices`, `desk` | Inventory, Accounting | P5 |
| `list_leases` | `leases`, `desk` | Facilities | P5 |
| `list_payments` | `payments` | Accounting, Facilities | P5 |
| `list_obligations` | `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` | Accounting | P5 |
| `list_approvals` | approval queue (`output/approvals.json`) | Boss, Accounting | P5 |
| `list_drafts` | drafts (`output/drafts.json`) | Boss, Customer Service | P5 |
| `prepare_payment` | reads `invoices`/`leases`, `cash_accounts`, `desk`; writes the approval queue | Accounting | P5 |
| `prepare_purchase_order` | reads `vendors`, `pricing`, `inventory`, `invoices`, `desk`; writes the approval queue | Accounting | P5 |
| `draft_customer_message` | writes drafts (`output/drafts.json`) | Customer Service | P5 |
| `update_ticket_status` | writes `tickets.status` | Boss | P5 |
| `pay` | writes `payments`, `cash_accounts`, and `invoices` (status → paid) or `leases` (next_due + 1 month) | **Human only** (board Approve button → `POST /api/approvals/{id}/approve`, or `backend/approve.py`) | P5 |
| `approve_purchase_order` | approval queue | **Human only** | P5 |
| `reject_request` | approval queue | **Human only** | P5 |
| `reset_database` | copies `campus_customs.db` → `campus_customs_new.db`; clears the queue and drafts | **Runner / human only** | P5 |

---

## Safety

**Guardrails for real customers and real money**
- **A human approves every payment.**
  - No agent has the `pay` tool. The MCP toolset is filtered per agent, and a second allowlist check runs on every call.
  - Agents can only *queue* a request with `prepare_payment`. A named person then approves it on the board (or in `backend/approve.py`), and their name is saved in `payments.approved_by`.
  - `pay` also rejects any `approved_by` that looks like an agent.
  - On the board, approving takes a typed name plus two clicks ("Tap again to pay $840.00"), and every approval or rejection is written to the audit trail as a `human_decision`.
  - Approvals are locked while a team run is in progress, so cash can't change while agents are reasoning about it.
  - The API only accepts browser calls from local pages (localhost / 127.0.0.1), so an outside website can't trigger an approval.
- **Money can't be faked or overdrawn.**
  - The payment amount comes from the database (the invoice or lease), not from the agent.
  - `prepare_payment` refuses if cash, after the other pending payments, can't cover the bill.
  - `pay` re-checks the bill and the balance inside one database transaction and refuses rather than let a balance go negative.
  - It also refuses double payments and requests where the bill changed after it was queued.
  - There is no tool that adds money; cash only goes out.
- **Verify before paying.** Facilities checks a rent notice against the lease (landlord, amount, due date) and against `payments`, so a fake or duplicate notice isn't paid.
- **No outside contact.**
  - No tool can email, text, or call anyone.
  - Customer messages are drafts on the board for a person to send.
  - Purchase orders are never sent to vendors.
  - Customer Service must not reveal internal details: costs, margins, cash, or bills.
- **Least privilege and identity.**
  - Each agent sees only its role's tools.
  - `prepared_by` and `drafted_by` are stamped by code with the real agent name, so an agent can't sign as another.
- **Respect vendor rules.** `list_vendors` and `prepare_purchase_order` flag a vendor that is blocked by an open unpaid invoice.
- **Same "today" for everyone.** Due dates use `desk.date_today`, never the real clock.
- **Start clean and keep records.**
  - Each full run first resets the working database from the untouched original.
  - Every step, tool call, delegation, and human decision is appended to the audit trail.

**Limits that keep token usage in check** (`backend/config.py`)
- Boss: at most 12 model requests, 20 tool calls, and 150k tokens per ticket run. Each specialist: 8 requests, 12 tool calls, and 80k tokens per run (PydanticAI `UsageLimits`).
- Delegation: at most 2 levels deep (Boss → specialist → specialist), and at most 8 delegations per ticket. No agent can call one already in its chain, which stops A↔B ping-pong.
- Time: each model request times out after 30 seconds, with up to 3 retries (the provider occasionally stalls a call). Each ticket has a 480-second limit, after which it is left for a human.
- Small context: each ticket runs separately. Tools return only the rows needed. Audit text fields are capped at 4,000 characters.

---

## Backend routes (Problem 7)

FastAPI app in `backend/main.py`. Start it from `backend/` with `uvicorn main:app --reload --port 8000`. Interactive docs are at `http://127.0.0.1:8000/docs`. CORS allows the Vite dashboard at `http://localhost:5173` (and other localhost ports).

- `GET /api/tickets`: Lists all tickets with their raw status and whether each is open or resolved.
- `POST /api/tickets/{ticket_id}/run`: Starts the agent team on one ticket in the background and returns a `run_id` right away. When the run finishes cleanly, the ticket is marked resolved; any queued payments stay in the approval queue. Returns 409 if a run is already going.
- `GET /api/runs/{run_id}`: Shows a run's status (running, done, or error), plus the Boss's decision and pending approvals when it finishes.
- `GET /api/events?limit=&after=&run_id=&ticket_id=`: Returns recent agent events from `output/audit_trail.json`: what each agent said and which tools it used. The board polls this with `after` to refresh.
- `GET /api/approvals?status=pending|all`: Lists the payments and purchase orders the agents queued for human approval.
- `POST /api/approvals/{approval_id}/approve` (body `{"approved_by": "<name>"}`): A human clicked Approve.
  - A payment runs the MCP `pay` tool. This is the only route that changes cash: it updates `payments`, `cash_accounts`, and `invoices` or `leases`, and refuses if cash is short.
  - A purchase order is marked approved; nothing is sent to the vendor.
- `POST /api/approvals/{approval_id}/reject` (body `{"rejected_by": "<name>", "reason": ""}`): A human rejected a queued payment or purchase order.
- `GET /api/cash`: Returns the current checking balance from `cash_accounts`, plus payments still waiting for approval.
- `GET /api/drafts?ticket_id=`: Returns customer message drafts on the board (never sent).
- `POST /api/reset`: Resets `campus_customs_new.db` to the original values and clears approvals and drafts so you can try a fresh run. The audit trail is kept.

---

## Dashboard (Problem 8)

React + Vite + TypeScript in `frontend/`. Start it with `npm run dev` (`http://localhost:5173`). It calls the backend at `http://localhost:8000`. The full design rationale is in `output/design.md`.

- **Layout:**
  - **Agent Team panel (left two-thirds):** the five agents.
  - **Right column:** the Tickets list on top, with Checking Account, "Needs your OK" approvals and drafts below.
- **Guidance:**
  - A three-step guide (Pick a ticket → Send the team in → Approve what they queue) highlights where you are.
  - The lime **Send the team in** button sits under the ticket name.
  - A "Your turn" banner and numbered steps show exactly where to type your name and click Approve.
- **Agents:**
  - Each one is a hand-drawn SVG character (no generated images) that pops out of its card.
  - Each card shows the agent's status (working, done, not called, or stuck), what it is doing in plain English, the MCP tools it used, and a "What I did" summary when it finishes.
- **Hand-offs:** a numbered arrow per hand-off, from the agent who handed off to the one who received the work. Repeats get separate lines, refused hand-offs are red with a ✕, and a tally reads, for example, "Boss → Accounting ×2".
- **Play-by-play:** a live timeline of every step, indented by delegation depth.
- **Resolved tickets:** a green ✓ Resolved pill and a RESOLVED stamp on the ticket card, plus the Boss's final call under the agents.
- **Cash:** the Checking Account balance rolls down and shows a red "−$840.00" chip when a payment is approved. A meter shows how much is already promised to queued payments.
- **Data:**
  - The board polls `/api/events` every 1.2 seconds during a run (6 seconds otherwise).
  - It reads tickets, cash, approvals and drafts from the routes above.
  - It ignores any run from before the latest reset.

---

## Output files

| File | What it is |
|---|---|
| `output/audit_trail.json` | Append-only record of every agent-loop step, tool call, hand-off, reset, and human decision |
| `output/approvals.json` / `output/drafts.json` | The live approval queue and message drafts (cleared on reset) |
| `output/latest_run.json` | Summary of the most recent run from `run_tickets.py` / the API |
| `output/desk_tickets.html` | Expected vs. actual plan per ticket, plus the Cash and Reflection tabs |
| `output/resolved_tickets.json` | Final status, outcome, agent contributions, and human approvals per ticket |
| `output/resolved_board.html` | Screenshots of the board for each resolved ticket |
| `output/design.md` | Dashboard design choices |
| `output/mcp_smoke.json` | Problem 4 MCP tool smoke tests |

---

## Resolved run (Problem 9)

The database was reset first, so the working copy was identical to `campus_customs.db` with checking at $3,400.00. Each ticket was then run from the board, one at a time. Full details are in `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json` and `output/resolved_board.html`.

| Ticket | Agents (hand-offs) | Human approval | Cash |
|---|---|---|---|
| 101 Bulldog tee | Boss → Inventory, Accounting, Customer Service (3) | PAY-001 $840 invoice 501, approved by Jay | $3,400 → $2,560 |
| 102 Rent due | Boss → Facilities + Accounting in parallel; Facilities ⇄ Accounting (4 done, 2 refused by the loop guard) | PAY-002 $2,400 rent, approved by Jay | $2,560 → $160 |
| 103 Bulk hoodies | Boss → Inventory, Accounting, Customer Service (3) | none (no restock queued: $264 > $160) | $160 → $160 |

The ending balance of **$160.00** matches `cash_accounts`, and `payments` holds exactly two rows, both `approved_by` Jay.
