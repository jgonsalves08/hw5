# Campus Customs MCP Server

A FastMCP server that is the **only source of shop facts** for the Campus Customs agent team. The team works the ticket queue: customer orders, rent notices, and price-override requests.

**Database:** `../data/campus_customs_new.db`, the working copy.
- Read tools open it in SQLite read-only mode.
- Only the guarded write tools below can change it.
- The original `../data/campus_customs.db` is never written. `reset_database` copies it back over the working copy before each full run.

**Workflow files:** The approval queue (`../output/approvals.json`) and message drafts (`../output/drafts.json`) are workflow state, not shop facts.

## Tools

### Read tools
| Tool | What it does |
|---|---|
| `check_inventory(sku, size=None, qty_requested=None)` | Confirms whether we carry a SKU and size, how many are on hand, and whether a requested quantity can be filled (including the shortfall). |
| `check_overdue(ticket_id)` | Uses the ticket type to find the related due date (`leases.next_due` for rent, `invoices.due_date` for linked invoices) and compares it to `desk.date_today`. |
| `check_price(sku, proposed_unit_price=None, qty=None)` | Returns unit cost, list price, margin, and the break-even discount. If you pass a proposed price, it also checks that the price stays above cost and calculates the order's profit. |
| `get_desk_today()` | The shop's "today" (`desk.date_today`). |
| `list_tickets(status="open")` | The ticket queue. |
| `get_ticket(ticket_id)` | One ticket plus the lease or invoice (with vendor) it links to. |
| `get_cash_balance()` | Cash per account, minus payments already waiting for approval. |
| `list_invoices(status=None)` | Vendor invoices, with days until due or overdue. |
| `list_vendors()` | Vendors with lead time, open unpaid invoices, whether they will ship new product, and ETA if ordered today. |
| `list_leases()` | Leases with rent, next due date, and days until due. |
| `list_payments()` | Payments already made. |
| `list_obligations(within_days=30)` | Open invoices plus rent due soon, measured against cash: total owed and cash left if everything is paid. |
| `list_approvals(status="pending")` | The human approval queue. |
| `list_drafts(ticket_id=None)` | Message drafts on the board. |

### Agent write tools (queue or draft only; no money moves)
| Tool | What it does |
|---|---|
| `prepare_payment(kind, ref_id, prepared_by, reason, ticket_id=None, account="checking")` | Queues an invoice or rent payment for human approval. The amount comes from the database. Refuses duplicates, already-paid bills, and anything cash can't cover. |
| `prepare_purchase_order(vendor_id, sku, size, qty, prepared_by, reason, ticket_id=None)` | Queues a restock order for human approval, with estimated cost, ETA, and a flag if the vendor is blocked by an open invoice. Nothing is sent to the vendor. |
| `draft_customer_message(ticket_id, to, subject, body, drafted_by)` | Saves a draft to the board. It is never sent. |
| `update_ticket_status(ticket_id, status)` | Sets `tickets.status` to `open`, `in_progress`, `waiting_on_approval`, or `resolved`. |

### Human-only tools (tag `human_only`; never given to an agent)
| Tool | What it does |
|---|---|
| `pay(approval_id, approved_by)` | Executes an approved payment in one transaction. It inserts into `payments`, lowers `cash_accounts.balance`, and either marks the invoice paid or moves `leases.next_due` forward one month. Refuses if cash is short (no negative balances) or if `approved_by` is not a named human. |
| `approve_purchase_order(approval_id, approved_by)` | Marks a purchase order approved. Nothing is sent to the vendor. |
| `reject_request(approval_id, rejected_by, reason)` | Rejects a pending payment or purchase order. |
| `reset_database()` | Copies `campus_customs.db` over the working copy and clears the queue and drafts. The audit trail is kept. |

## Run

Dependencies are in `requirements.txt` at the HW5 root. From the HW5 folder:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python mcp_server/server.py          # stdio
.venv/bin/python mcp_server/server.py --http   # http://127.0.0.1:8002/mcp
```
