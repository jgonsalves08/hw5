# HW5 — AI Prompts Log

This file records the prompts used for each problem, any follow-up prompts, and a short note on what the first response was missing.

---

## Problem 2: Study the Campus Customs database

**Initial prompt:**

> Let's start Problem 2: Study the Campus Customs database. Open the campus_customs.db for me so I can look through all the tables and their fields. I've created a copy of the database already (called campus_customs.new.db) which is the database we will be using. I also need to review the three open tickets so I can see how they relate to the other tables. Lastly, I need you to create a file called harness.md (put it under the output folder) and this file should list the fields for each table within the database and a short line description on why that table matters for the agents that will be created in a later problem (this file will also be added onto in later problems too)

**Follow-up prompt (if needed):**

> _(to be added)_

**What was lacking after the first prompt:** _(to be added)_

---

## Problem 3: Build the MCP server

**Initial prompt:**

> Let's start Problem 3: Build the MCP server. We need to write an MCP server within the mcp_server folder using FastMCP. I need to write three tools that can be used for the tickets in the database. Create a file called harness.md and put it in the output folder. Within this file, list each of the three MCP tools created (see below for the three I'm thinking), and for each tool make sure to write which table it reads, which ticket it helps unlock (so either 101, 102, or 103), and one sentence on why that tool is the right one for that specific ticket. This one sentence should not be something like "reads inventory", it should be longer than that. Additionally, add a short README.md file within the mcp_server folder that explains what the MCP server is for, which database file it uses, and the three tools it has.
>
> These are the three tools I'm thinking:
>
> 1. check inventory -check to see if the requested item is something we stock in inventory, and if it is, see how much we have in stock (if it's in stock)
> 2. overdue check - checks what type ticket type it is and checks the respective table to pull the due date and compare if the ticket is overdue (if it can be overdue) based on the current date (desk.date_today).
> 3. check price - check the price of the item (if this is something we stock) in order to determine if this is something that can be discounted

**Follow-up prompt (if needed):**

> I think within the harness file it doesn't have to only be assigned to one ticket. It can describe how it helps multiple tickets

**What was lacking after the first prompt:** The harness assigned each tool to exactly one ticket. That hid how the tools overlap: `check_inventory` also matters for 103, and `check_overdue` and `check_price` also matter for 101.

**Follow-up prompt 2:**

> Make sure the requirements.txt file is outside of the mcp_server file

**What was lacking after the previous prompt:** `requirements.txt` (and the venv) were created inside `mcp_server/`, but they belong at the HW5 project root so later problems share the same environment.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

**Initial prompt:**

> Let's start Problem 4: Add the MCP server to vibe coder and test each tool. The MCP should be added to the project and the connection should be saved as a json text in .mcp.json at the project root. Test each of the three mcp tools and save the evidence in mcp_smoke.json in the output folder. For each tool include the prompt we asked the vibe coder, the tool name, and the tool output (which must match the values in data/campus_customs_new.db)

**Follow-up prompt (if needed):**

> _(New session, so the campus-customs MCP tools would load for testing)_
>
> Using the campus-customs MCP, check inventory for ticket 101: one Classic Bulldog Tee (CC-TEE-WHITE) in size S.
>
> Yes save it to mcp_smoke.json and start it with this prompt, the tool name, and the tool output (which should match values in data/campus_customs_new.db). Then run these prompts to check the other tools:
>
> - "Using the campus-customs MCP, check whether ticket 102 is overdue."
> - "Using the campus-customs MCP, check the price of CC-HOOD-NAVY for ticket 103 if we sold 20 at $45 each."
>
> yes, switch .mcp.json to relative paths

**What was lacking after the first prompt:** The MCP tools weren't available to call in the original session, so I had to start a new session to get them working and run the smoke tests. The `.mcp.json` also used absolute paths to my own computer, so the MCP connection would break for anyone running the submitted project on another machine.

---

## Problem 5: Build the agent team and grow the MCP tools

**Initial prompt:**

> Let's start Problem 5. Ok now we need to build the agentic team for campus customs using pydanticAI. I would like to have 5 agents:
>
> 1. Boss Agent - this agent should read each of the tickets, and then decide which of the other agents should work on it, and then lastly make the final decision if need be
> 2. Inventory Agent - this agent should check the stock of the product by SKU and size, should spot any shortfalls, and figure out which vendor can restock
> 3. Accounting Agent - this agent should watch all cash and invoices, check any margins, and then prepare any payments or purchase orders for human approval
> 4. Facilities Agent - this agent will handle the shop space side (so anything to do with leases, rent, etc)
> 5. Customer Service Agent - this agent drafts messages for customers (but doesn't send it to anyone)
>
> This should include any prompts, models, and agent loops so they can delegate work to each other with full connectivity. The agent prompts should be put in backend/prompts/ and should be one file per agent. The data types should be put in backend/models.py and the agent files should be put under backend/. Make sure the five roles are clear. Use The PORTKEY_API_KEY within the .env file (don't write the actual key in the .env.example file) and only use gpt-6-luna. Any other additional tools that are needed for the agents should be created and put in the MCP server so they can work on the open tickets. The shop facts should ONLY come from the MCP server over data/campus_customs_new.dp (there should not be anything else created for shop facts).
>
> The agents should append the stuff they do to the output/audit_trail.json as they run. So for each agent-loop step, there should be enough stuff recorded to audit later on and things should be appended to the file, not wiping after each run. Then in the output/harness.md, list each agent and each MCP tool (along with the ones added in the problem) and which table the tool uses. Lastly, there should be a short safety section which should include the guardrails a real business would want when agents work with real customers and real money, plus any limits that keep token usage in check. The mcp_server/README.md should be updated so the tool list matches what we have now.
>
> Here are the rules of the shop:
>
> * The field desk.date_today is "today" for the shop. This date should be used to determine what is overdue
> * Vendor lead times come form the vendors table
> * A vendor will not ship new product while they still have an open unpaid invoice
> * Human approval is required for any payments. THIS NEEDS TO BE FOLLOWED (since points on HW will be deducted if this is not done). Now if a payment is made, the relevant table needs to be updated
> * If there is not enough cash, the pay tool must refuse. So there should never be any negative balances
> * Cash only goes out, so no money should ever come in
> * Before a full run to resolve the tickets, the database should be reset to the original values
> * Customers or vendors should NOT be emailed or called. The drafts should just stay on the board
>
> The PORTKEY_API_KEY should be used for all AI calls and ONLY gpt-6-luna should be used through the Portkey for every agent. Use pydantic-ai-slim[openai,mcp]

**Follow-up prompt (if needed):**

> _(to be added)_

**What was lacking after the first prompt:** _(to be added)_

---

## Problem 6: Plan the three tickets

**Initial prompt:**

> Let's start Problem 6: Plan the three tickets. Create an html file, output/desk_tickets.html that you can double-click into with one tab per ticket (so one for 101, one for 102, and one for 103). Also add empty Cash and Reflection tabs for later problems (these can have "coming later" notes for now). For each ticket tab have an Expected section and an Actual section. Leave the Actual section blank for now, the Expected section are going to be what I expect the team to do on each open ticket which should include the following things:
>
> * Who the Boss should call first and why
> * All the agent delegations I expect
> * Which MCP tools I expect that run to use
>
> So this is what I'm thinking will happen
>
> * Ticket 101
>    * Who the Boss should call first and why: I think the boss will call the inventory agent first because this is a customer order requesting a product, so we need the inventory agent to start looking into inventory
>    * All the agent delegations I expect: The agent may delegate to accounting for invoicing problems since it's overdue and may delegate to customer service to reach out to the customer to update them on the status
>    * Which MCP tools I expect that run to use: The tools I expect to be used are check_inventory, check_overdue, check_price, all ticket tools, and draft_customer_message
> * Ticket 102
>    * Who the Boss should call first and why: The boss I think is going to call the facilities agent first since this ticket deals with rent
>    * All the agent delegations I expect: the facilities agent will probably delegate to accounting since they deal with payments
>    * Which MCP tools I expect that run to use: all the ticket tools, list_leases, list_payments, list_approvals, prepare_payment, update_ticket_status, pay
> * Ticket 103
>    * Who the Boss should call first and why: The boss will likely call the inventory agent first since this deals with products within inventory
>    * All the agent delegations I expect: the inventory agent will delegate to accounting and customer service agents again
>    * Which MCP tools I expect that run to use: This will use the check_inventory, check_overdue, check_price, all ticket tools, draft_customer_message

**Follow-up prompt (if needed):**

> You're right, remove the pay from the expected plan for 102
>
> Remove check_overdue from 103 expected plan as well

**What was lacking after the first prompt:** My expected plan for ticket 102 listed `pay` as a tool the agent run would use, but no agent can call `pay`; it only runs when a human approves the payment after the run. Ticket 103 also listed `check_overdue`, but that ticket has no lease or invoice, so there is nothing for it to be overdue on.

---

## Problem 7: Backend routes

**Initial prompt:**

> Let's start Problem 7: Backend routes. In backend/main.py, use FastAPI and add routes that do the following:
>
> * Return the three tickets and whether each is open or resolved
> * Take a ticket id and run the agent team on that ticket
> * Return recent agent events (what each agent said and which tools they used) so the board can refresh (we will create frontend dashboard in next problem)
> * Approve a payment or purchase after a human clicks approve (agents only prepare the apy, this route is what actually changes cash)
> * Return the current checking balance from cash_accounts
> * Reset the database to the original values when you want to try a fresh run
>
> From the backend/ folder start the server with: uvicorn main:app --reload --port 8000
>
> In output/harness.md list each route in one line (what URL/ what it does)

**Follow-up prompt (if needed):**

> _(to be added)_

**What was lacking after the first prompt:** _(to be added)_

---

## Problem 8: Agent dashboard

**Initial prompt:**

> Let's go to problem 8. Now let's build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes build in Problem 7. The board should:
>
> * List all three tickets
> * Let us pick one ticket and start the agent team on it
> * Show each agent and what they are saying / doing while the ticket runs
> * Mark a ticket resolved when the run finishes
> * Show a short summary of what each agent did on that ticket
> * Let a human approve a pay or purchase when asked
> * Show the checking balance (it should drop after an approved pay)
>
> The dashboard should look great too. Make it look similar to the picture where the agents look popped out, the color in the background is a nice shade of green. And make it look very neat and clean with a cool font. Give each agent a picture based off their role. The front end should talk to the backend at http://localhost:8000. For the backend, allow the Vite page origin (likely http://localhost:5173) so the browser is allowed to call the routes. The board should start with: npm run dev. Then create output/design.md where it should have what we chose for the dashboard look (layout, how the agents read differently, how resolved tickets and cash show up) and why. This should include the creative choices that make it feel special and something humans would actually enjoy using

**Follow-up prompt (if needed):**

> Here's the picture _(reference image: green furniture-shop app concept)_
>
> Hm I think having the layout left to right like that actually is a bit confusing. So have the Ticket panel be on the right side. Let the agent panel (which change the title of that panel from Bulldog Tee title to Agent Team title) and let that take up 2/3rds of the page since that is the brunt of the work. And then below the ticket panel have the 3rd panel (may need to make the ticket panel a bit smaller to make everything look cleaner)
>
> I think it looks great, just need to make it a little easier for someone to understand what they need to do (like where to click to have the team work on a ticket), if the human needs to approve something, show they clearly where they need to type/click to approve, etc
>
> So for the instructions #2 (Send the team in), it says select the white button under the ticket name, isn't it black?
>
> Ok maybe remove the black arrow buttons because it is kind of confusing for a user. I thought I needed to click it
>
> I like that it shows each agent working, can you also draw lines when there are hand offs across agents (so for example when the boss hands off to Accounting, when Accounting hands off to Facilities). If there are multiple hand offs between each agent, so each hand off as a separate line so we can so how many times they hand off
>
> And show it with arrows so we know who handed off to who
>
> Also for the Checkings Panel, can you rename to "Checkings Account" to make it easier to understand what it is showing

**What was lacking after the first prompt:** The reference picture didn't come through with the first prompt, and the first three-column layout (tickets, agents, cash side by side) was confusing, so the agent panel needed to be the main two-thirds of the page with tickets and cash stacked on the right. It also wasn't obvious to a new user where to click to start the team or where to type and click to approve a payment, so the board needed step-by-step guidance. The guide also described the start button as white (it is lime green), and the black arrow buttons on the ticket cards looked like something you had to click, so they were removed. Finally, the board didn't show how the agents handed work to each other, so it needed numbered arrows, one per hand-off.

---

## Problem 9: Resolve the tickets

**Initial prompt:**

> Let's start Problem 9: Resolve the tickets. So double check I've reseted the working database (campus_customs_new.db) and note the starting checking balance (currently I'm seeing $3,400). I'm going to test each ticket on the board one by one until each are resolved. I'd like you to fill out the Actual sections within the desk_tickets.html file for each ticket as I test each one. Remember this should show which agents worked, what they delegated, and which tools they used. Don't touch the Expected section as I'd like to compare the two. Then within the Cash tab of the file, I'd like you to itemize the money by:
>
> * Showing the starting checking balance (after it's been reset/if it's reset properly)
> * For each of the tickets show how cash changed when that ticket was resolved and why (so which pay / purchase, the dollar amount, etc)
> * And then the ending checking balance. This must match cash_accounts in the working database
>
> Then create a resolved_tickets.json file in the output folder that shows for each ticket: the id, the final status, a short outcome description, what each agent contributed, and any human approvals.
>
> Also create a resolved_board.html in the output folder that is a page you can double click with a screenshot of the React board for each resolved ticket (101, 102, and 103).
>
> The real runs should be added to the audit_trail.json in the output folder. And then finish filling out the harness.md file in the output folder so it covers all tables, MCP tools, the five agents, API routes, the dashboard, and the safety rules. Let me know when I can start testing the agents on the full run through

**Follow-up prompt (if needed):**

> _(to be added)_

**What was lacking after the first prompt:** _(to be added)_

---

## Problem 10: Reflection

**Initial prompt:**

> Let's start Problem 10: Reflection. I need to answer the following questions and put my answers within the Reflection tab of the desk_tickets.html:
>
> 1. How would you evaluate the performance of the agents on each ticket and why?
> 2. For each ticket, how did Actual compare to the Expected plan you wrote earlier?
> 3. What would have been simpler as one agent with tools -- and why?
> 4. Describe three new problems Campus Customs might face that this agent team could solve with the tools you built
> 5. Describe three new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them
>
> I'll put my thoughts for each question below and of course clean it up a bit to sound better. Also each answer needs to tie to this app and the three tickets ran. The ticket tabs and Cash tab need to be used on the same page as my evidence. Here are my thoughts:
>
> 1. On ticket 101, I thought it did a great job handling everything. It queued the $840 payment for me to approve, once I approved it, the checking balance went down to $2,560. On ticket 102, I thought it did ok, the boss called Facilities and Accounting at the same time and then they both called each other. This caused the work to be doubled, but I'm glad it refused the loop through the safe guard, but it did take a bit more time (4.5minutes). It did ask me to approve the rent payment of $2,400 which I did and then have the ending balance change for checking to $160. On ticket 103, I thought it did a good job recommending a counter offer and chose not to queue anything for approval since we did not have enough money left to pay (since we only had $160 left). The one thing it didn't do well for 103 ticket was the draft hinted at internal money trouble to the customer, which we'd probably want to avoid in real life
> 2. In terms of actual vs. compared, for 101 I got correct which agents would be called, but I thought the agents would hand off to each other (like Inventory to Accounting) while the Boss actually handed it off, which makes more sense (in most cases). Additionally there were a few tools that I expected but were not used (like check_overdue, list_tickets) and a bunch used but were not expected (like list_invoice, get_cash_balance). On ticket 102, I got a bit right (like calling facilities and accounting) but once again did not get accurately who would call/hand off to who. And in this case there were attempts to hand off/doubling the work. On ticket 103, once again I was correct on which agents will be called at some point, but did think the boss would be the one to do the hand offs (which makes more sense). I also did not get some of the tools correct either (like list_invoices, list_vendors, get_cash_balance)
> 3. I think any instance where agents were not working at the same time, it probably would have been simpler to have one agent work on it. So for example ticket 103. Also the hand back and forth on ticket 102 would not have occurred if it was just one agent, but I definitely think it makes sense to break out these tasks into multiple agents
> 4. 3 new problems Campus Customs might face that the agent can solve with the tools it has are:
> 5. 3 new problems Campus Customs might face that the agent can solve with the tools it has are:

**Follow-up prompt (if needed):**

> Sorry I didn't get to finish problem 4 and 5. I'll continue that now
>
> I think those 3 things for Question 4 looks good, I think for the 2nd recommendation (restocking something sold out for a vendor with no unpaid invoices), I think it should be general like what I wrote and then within the example show that it could be crest mug that is restocked vs. being so specific. And I like the Question 5, 3 things we could not solve with our current agents and what needs to be done to solve it. I think it's comprehensive and tackles what needs to be done/added

**What was lacking after the first prompt:** My first prompt left Questions 4 and 5 unfinished, and the drafted second example for Question 4 was too specific (only the Crest Mug) instead of describing the general restock problem with the mug as an example.

---

## Problem 11: Submit to GitHub

**Initial prompt:**

> Let's start Problem 11: Submit to GitHub. So we need to push the code to a public Github repository (using my account) so graders can clone it. I'll need to submit the repo URL so please give it to me and also put it in the github_url.txt file in the output folder. Remember, my real .env file should NOT be pushed to Github (the .env example should). Both database files under data/ SHOULD be included in the push. See the expected layout in the picture (if I'm missing any files currently, let me know so I can see what was missed and how the file should be filled out). The README within the project root should explain copying the original database to the working copy when you need a clean run, starting the MCP server, starting FastAPI backend, starting the React board, and resetting the working database before a full three-ticket run

**Follow-up prompt (if needed):**

> _(to be added)_

**What was lacking after the first prompt:** _(to be added)_
