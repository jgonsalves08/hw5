# Campus Customs Ticket Desk — Dashboard Design

The board lives in `frontend/` (React + Vite + TypeScript) and talks to the FastAPI backend at `http://localhost:8000`. Start the backend from `backend/` with `uvicorn main:app --reload --port 8000`, then start the board from `frontend/` with `npm run dev` (`http://localhost:5173`).

## The look, and where it came from

The visual reference was a furniture-shop concept: deep green backgrounds, soft pale "phone" cards, products that pop out over the top edge of their cards, black pill buttons, and a tight, bold geometric font. We borrowed that language and gave it a job.

- **Green canvas on a white page.** The board sits on an off-white page. The work area is one large rounded block with a forest-to-olive gradient (`#12261a` → `#93bd5b`) and two soft glows. Green says "money and go," it's calm enough to stare at during a run, and it makes the pale cards on top feel lifted.
- **Font: Plus Jakarta Sans** (self-hosted, so it works offline). It's set heavy (800) with tight negative letter-spacing for headlines and dollar amounts, like the reference. Tool names use **JetBrains Mono**, so anything that is a literal MCP tool looks like code and reads differently from what an agent says.
- **Black as the "action" color.** Black pills mark status and IDs (like the reference's "-5%" tags). Solid black buttons are reserved for the decisions that matter: *Reset desk* and *Approve & pay*. The one lime-green pill button sends the team in. If it's black or white and pill-shaped, a human is about to make something happen.

## Layout

```
┌──────────────────────────────── Campus Customs · Desk open 2026-08-31 ──── [Reset desk] ┐
│ ┌──────────────── Agent Team (2/3) ───────────────┐  ┌──── Tickets (1/3) ────┐            │
│ │  Working on: #101 · Bulldog tee                 │  │ All · Open · Resolved │            │
│ │  [ Boss — wide card, crown, final call ]        │  │ #101 tee (pops out)   │            │
│ │  [Inventory][Accounting][Facilities][Customer…] │  │ #102 shop             │            │
│ │  Boss's call (decision card)                    │  │ #103 hoodie           │            │
│ │  ( ▶ Send the team in on #101 )  ← lime button │  └───────────────────────┘            │
│ │  Play-by-play feed                              │  ┌─ Checking $3,400.00 ──┐            │
│ └─────────────────────────────────────────────────┘  │ Needs your OK · Drafts│            │
│                                                       └───────────────────────┘            │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **The Agent Team panel takes two-thirds of the width** because it's where the work happens. It is the one *dark* panel, like the dark center phone in the reference, so the eye lands there first.
- The title is "Agent Team". The selected ticket appears underneath as "Working on #101 · Bulldog tee" with the customer's note, so you always know what the team is doing without the title changing.
- **The right column is the human's side of the desk.** The compact Tickets list is on top (pick what to work on). Cash & approvals sit below it (approve what the team asks for). The flow reads naturally: pick a ticket on the right, watch the team on the left, then approve on the right.
- Under 1,500px the four specialists wrap to a 2×2 grid. Under 1,000px everything stacks into one column, with tickets first.

## Always knowing what to do next

People opening the board for the first time shouldn't have to guess where to click, so the board tells them.

- **A three-step guide sits above the canvas:** ① Pick a ticket → ② Send the team in → ③ Approve what they queue.
  - The current step has a black ring and a lime **"You are here"** tag. Finished steps turn into green checks.
  - Step 3 turns amber, with a count, when something is waiting.
  - Each step is clickable and jumps to the place you need: the ticket list, the run button, or the approval box.
- **The start button is the first thing under the ticket name**, not buried below the agents. When it's ready, it turns lime and gently glows ("▶ Send the team in on #101").
  - A one-line hint under it always says what happens next: what the Boss will do, that another ticket is busy, or that the ticket is done.
- **Tickets say "Click a ticket to open it on the left,"** and the chosen card gets a black outline and a lime **Selected** tag.
- **When the team queues something that needs a person, the board says "Your turn"** in an amber banner right under the run button.
  - Clicking **Approve it →** scrolls to the approval box and puts the cursor in the name field.
- **The approval box spells out the two moves:** "① Type your name in the box below" and "② Click Approve on a request, then click again to confirm." The current step is highlighted.
  - Until a name is typed, the name box pulses with an amber ring, and the Approve button reads "Add your name to approve" instead of looking clickable.

## How the agents read differently

Each agent is a hand-built SVG character: the same friendly "bean," with a body color and a prop that says what it does. They are drawn in code, not generated images. Like the chairs in the reference, each one **pops out over the top edge of its card** with a soft drop shadow.

| Agent | Color | Prop | Why |
|---|---|---|---|
| Boss | charcoal green | gold crown + red tie | in charge and makes the final call |
| Inventory | orange | green cap + labeled cardboard box | stock, shelves, shipments |
| Accounting | green | round glasses, calculator, gold coin | money and margins |
| Facilities | yellow | orange hard hat, little shop, key | the building and the lease |
| Customer Service | coral | headset + envelope with a heart | talks to customers (drafts only) |

**The Boss gets a wide featured card** above the four specialists, which matches the hierarchy: the Boss routes, the others work.

**Every agent's mood is visible at a glance:**
- **Working:** the card lifts and gets a ring in the agent's color. The character bounces and its eyes dart side to side. A black status pill pulses, and typing dots appear in the speech bubble.
- **Done:** the character smiles with happy closed eyes. The bubble switches to **"What I did"** with the agent's own one-line summary, so each agent's card *is* its summary on that ticket.
- **Not called:** the card fades and the character turns gray. Facilities sitting out a tee order is information too.
- **Stuck:** a red pill, a worried mouth, and a sweat drop. This shows if a run times out or the backend restarts mid-run.
- While a run is going, agents who haven't been called yet say *"Standing by in case the team needs me…"* instead of looking finished.

The **speech bubble** shows what the agent is doing right now, in plain English, for example "Pulling up the lease…", "Asking Accounting for help", or "Queuing a payment for your approval…". The raw MCP tool names collect as mono chips under each card, and hand-offs are listed ("Handed off to Inventory, Accounting"). The **play-by-play feed** at the bottom is a color-coded timeline with a mini avatar per agent. Hand-offs are indented by delegation depth, so you can see Boss → Facilities → Accounting as a nested conversation.

## Seeing who handed off to whom

The team's teamwork is drawn right on the board.

- **Every hand-off is its own arrow**, from the agent who handed off to the agent who received the work. If the Boss hands off to Accounting twice, you see two parallel arrows, so you can count the hand-offs at a glance.
- **Arrows are numbered in order** (①, ②, ③…), so you can replay the conversation: Boss → Facilities ①, Boss → Accounting ②, Facilities → Accounting ③…
- **Each arrow takes the color of the agent who handed off.** The arrowhead sits on the receiving agent's card.
- **Placement:**
  - Arrows from the Boss drop into the top-left corner of each specialist's card, clear of the avatar and the status pill.
  - Hand-offs between specialists side by side dip in arcs below the row. Each repeat goes a little deeper, so the arcs never sit on top of each other.
- **State is visible on the line itself:**
  - A hand-off in progress has a flowing dashed line.
  - A finished one is solid.
  - A hand-off blocked by a guardrail (a loop or the delegation budget) is red and dashed, with a ✕ instead of a number.
- **A tally row** under the cards sums it up: "Hand-offs 5 · Boss → Facilities ×1 · Facilities → Accounting ×1 · Accounting → Facilities ×1, 1 refused".

## How resolved tickets show up

- When a run finishes, the backend marks the ticket resolved. The ticket card gets a green **✓ Resolved** pill, and a **RESOLVED** rubber stamp slams onto the card with a small bounce. The product art desaturates slightly.
- The run button changes to "✓ Resolved — reset the desk to run it again" so nobody re-runs a finished ticket by accident.
- A white **"Boss's call"** card slides up under the agents with the final decision.
- A ticket can be resolved and still have a payment waiting. A yellow "1 needs your OK" pill on the ticket makes that obvious, and the bell on the Tickets panel shows the total waiting.
- The Open/Resolved chips filter the list, with counts.

## How cash shows up

- **The Checking Account balance is the biggest number on the right side** ($3,400.00), in the same heavy style as the reference's prices. Below it:
  - a meter showing how much of the balance is already promised to queued payments
  - "Queued $X" and "Left after $Y". "Left after" turns red when it drops under $500.
- **When a payment is approved, the balance visibly drains.** The number rolls down to the new value, the figure shakes once, and a red **−$840.00** chip floats up and fades. You *see* money leave instead of noticing a number changed.

## Approving payments safely

- **Agents can only queue.** Every request lands in "Needs your OK" as a card. Each card shows:
  - the payee and amount
  - an overdue or due-in-N-days pill
  - the queuing agent's avatar and its reason, in its own words
  - the checking balance after paying
- **A name is required.** "Approving as ___" is saved in the browser and sent as `approved_by`. With no name, the button says "Add your name to approve".
- **Two taps to pay.** The first tap turns the button deep green and pulsing: "Tap again to pay $840.00". It resets after 5 seconds. Reset desk also needs a second tap. Money and resets should never happen from one stray click.
- Requests linked to the selected ticket get a lime outline. The card warns ahead of time if cash can't cover it, because the backend `pay` tool will refuse.
- Decided requests drop into a short history ("✓ PAY-001 · $840.00 to Bulldog Print Co — paid by …").
- **Drafts** sit below with an envelope icon and a "not sent" tag. You expand one to read the full message. Nothing on this board can email or call anyone.

## Small things that make it pleasant

- Characters blink and float gently when idle, so the board feels alive without being noisy.
- Toast pills at the bottom confirm every action ("Ticket #101 resolved — the team is done.") and turn red for problems.
- If the backend is down, a clear banner says so and gives the exact command to start it.
- The board polls every 1.2 seconds during a run and every 6 seconds otherwise. It picks up runs started from the command line too, and it ignores anything from before the last reset, so a fresh desk always looks fresh.
- Everything is keyboard-reachable, with a visible lime focus ring.
