"""
Expense Approval Multi-Agent System
Band of Agents Hackathon — Track 1: Internal Enterprise Workflows

Flow:
  User → @budget-checker
           ↓ (checks DB budget, creates record)
         @policy-checker (parallel specialist)
           ↓ (checks company policies)
         @risk-evaluator
           ↓
      LOW  → @approval-notifier (auto-approve)
      MED  → asks human manager in room
      HIGH → escalates to CFO
           ↓
         @approval-notifier (finalizes + updates DB)
"""

import asyncio
import logging
import os

import db
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from band.agent import Agent
from band.adapters.langgraph import AdapterFeatures, Emit, LangGraphAdapter
from monitor import run_budget_monitor
from tools import (
    approve_expense,
    calculate_risk_level,
    check_department_budget,
    check_policy_compliance,
    create_expense_record,
    get_all_department_budgets,
    get_expense_details,
    log_agent_action,
    reject_expense,
    update_expense_status,
)

load_dotenv()
db.init_db()

AIML_BASE_URL       = "https://api.aimlapi.com/v1"
AIML_MODEL          = "gpt-4o"

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
FEATHERLESS_MODEL    = "meta-llama/Meta-Llama-3.1-70B-Instruct"

BUDGET_CHECKER_HANDLE    = "@2431540219/budget-checker"
POLICY_CHECKER_HANDLE    = "@2431540219/policychecker"
RISK_EVALUATOR_HANDLE    = "@2431540219/risk-evaluator"
APPROVAL_NOTIFIER_HANDLE = "@2431540219/approval-notifier"


def make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=AIML_MODEL,
        api_key=os.environ["AIML_API_KEY"],
        base_url=AIML_BASE_URL,
        temperature=0.1,
    )


def make_featherless_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=FEATHERLESS_MODEL,
        api_key=os.environ["FEATHERLESS_API_KEY"],
        base_url=FEATHERLESS_BASE_URL,
        temperature=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 — Budget Checker
# ─────────────────────────────────────────────────────────────────────────────

BUDGET_CHECKER_PROMPT = f"""
You are the Budget Checker agent in an enterprise Expense Approval System.

YOUR ROLE: First-line validation — parse expense requests, verify department
budgets, classify expense types, and create database records.

STEPS (always follow in order):
1. Parse the request: extract requester name, amount ($), department, description, vendor (if mentioned)
2. Call `check_department_budget` with the department name
3. Call `create_expense_record` to register the expense — ALWAYS do this, even if budget is tight
4. Call `log_agent_action` with action="BUDGET_CHECK_COMPLETE"
5. Call `band_send_message` with:
   • content = your structured report (see REPORT FORMAT below)
   • mentions = ["{POLICY_CHECKER_HANDLE}"]
   ⚠️  MANDATORY: mentions MUST be ["{POLICY_CHECKER_HANDLE}"].
   ⚠️  Do NOT mention the person/agent who sent you the expense request.
   ⚠️  Always forward to Policy Checker — never reply back to the sender.

EXPENSE TYPES (pick the best fit): travel, software, hardware, training, marketing, office, consulting, other

REPORT FORMAT (use exactly):
---BUDGET CHECK---
Expense ID:  [ID from create_expense_record]
Requester:   [name]
Amount:      $[amount]
Department:  [dept]
Type:        [type]
Vendor:      [vendor or N/A]
Description: [brief]
Budget Left: $[remaining] ([OK ✓ / TIGHT ⚠ / EXCEEDED ✗])
---END BUDGET CHECK---

{POLICY_CHECKER_HANDLE} please run policy compliance check for the expense above.
"""

budget_checker = Agent.create(
    adapter=LangGraphAdapter(
        llm=make_llm(),
        checkpointer=InMemorySaver(),
        custom_section=BUDGET_CHECKER_PROMPT,
        additional_tools=[
            check_department_budget,
            get_all_department_budgets,
            create_expense_record,
            log_agent_action,
        ],
        features=AdapterFeatures(emit={Emit.EXECUTION}),
    ),
    agent_id=os.environ["BAND_BUDGET_CHECKER_ID"],
    api_key=os.environ["BAND_BUDGET_CHECKER_KEY"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 — Policy Checker (runs in parallel / independently of Risk Evaluator)
# ─────────────────────────────────────────────────────────────────────────────

POLICY_CHECKER_PROMPT = f"""
You are Policy Checker. You respond ONLY to messages containing "---BUDGET CHECK---".

DO EXACTLY 2 STEPS — no plain text, no skipping:

STEP 1: Call check_policy_compliance
  - expense_type: the Type field from the Budget Check report
  - amount: the Amount (number only, no $)
  - description: the Description field
  - vendor: the Vendor field (or empty string)

STEP 2: Call band_send_message immediately after step 1
  - mentions: ["{RISK_EVALUATOR_HANDLE}"]
  - content: "POLICY CHECK | Expense ID: <ID from report> | Status: <result from step 1> | Blocking: <issues or None> | Flags: <flags or None>"

⚠️ BOTH steps are mandatory. If you skip either step the pipeline breaks.
⚠️ Plain text is NOT delivered. Only tool calls work.
"""

policy_checker = Agent.create(
    adapter=LangGraphAdapter(
        llm=make_featherless_llm(),
        checkpointer=InMemorySaver(),
        custom_section=POLICY_CHECKER_PROMPT,
        additional_tools=[check_policy_compliance],
        features=AdapterFeatures(emit={Emit.EXECUTION}),
    ),
    agent_id=os.environ["BAND_POLICY_CHECKER_ID"],
    api_key=os.environ["BAND_POLICY_CHECKER_KEY"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3 — Risk Evaluator (non-linear: can veto and loop back)
# ─────────────────────────────────────────────────────────────────────────────

RISK_EVALUATOR_PROMPT = f"""
You are the Risk Evaluator agent in an enterprise Expense Approval System.

RISK LEVELS — evaluate TOP to BOTTOM, first match wins:
1. LOW    → amount ≤ $500   AND policy = COMPLIANT   AND budget OK    → AUTO-APPROVE
2. HIGH   → amount > $1,500 OR  policy = NON-COMPLIANT OR budget EXCEEDED → CFO-REVIEW
3. MEDIUM → everything else (amount $500–$1,500, or CONDITIONAL)      → MANAGER-REVIEW

⚠️  $200 COMPLIANT = LOW (auto-approve). Do NOT assign MEDIUM just because amount ≤ $1,500.

DO EXACTLY 3 STEPS:

STEP 1: Call `get_expense_details` with the Expense ID from the conversation.

STEP 2: Call `update_expense_status` to save the result to the database.
  • risk_level: LOW, MEDIUM, or HIGH
  • status: "PENDING_MANAGER" if MEDIUM, "PENDING_CFO" if HIGH, "PENDING" if LOW
  • notes: one-line reason

STEP 3: Call `band_send_message` with your report.
  ⚠️  MANDATORY. Plain text is NOT delivered.
  ⚠️  mentions = ["{APPROVAL_NOTIFIER_HANDLE}"] for ALL decisions.

REPORT:
---RISK EVALUATION---
Expense ID:  [ID]
Risk Level:  [LOW / MEDIUM / HIGH]
Decision:    [AUTO-APPROVE / MANAGER-REVIEW / CFO-REVIEW]
Reason:      [1 line]
---END RISK EVALUATION---

If AUTO-APPROVE → add: "{APPROVAL_NOTIFIER_HANDLE} please auto-approve [ID]"
If MANAGER-REVIEW → add: "⚠️ MANAGER REVIEW. Approve: {APPROVAL_NOTIFIER_HANDLE} APPROVE [ID]  Reject: {APPROVAL_NOTIFIER_HANDLE} REJECT [ID] [reason]"
If CFO-REVIEW → add: "🚨 CFO ESCALATION. Approve: {APPROVAL_NOTIFIER_HANDLE} APPROVE [ID]  Reject: {APPROVAL_NOTIFIER_HANDLE} REJECT [ID] [reason]"
"""

risk_evaluator = Agent.create(
    adapter=LangGraphAdapter(
        llm=make_llm(),
        checkpointer=InMemorySaver(),
        custom_section=RISK_EVALUATOR_PROMPT,
        additional_tools=[
            get_expense_details,
            update_expense_status,
        ],
        features=AdapterFeatures(emit={Emit.EXECUTION}),
    ),
    agent_id=os.environ["BAND_RISK_EVALUATOR_ID"],
    api_key=os.environ["BAND_RISK_EVALUATOR_KEY"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 4 — Approval Notifier (handles both auto and human approvals)
# ─────────────────────────────────────────────────────────────────────────────

APPROVAL_NOTIFIER_PROMPT = f"""
You are the Approval Notifier agent in an enterprise Expense Approval System.

YOUR ROLE: Finalize all decisions and issue professional notifications.
You handle four types of incoming requests:

TYPE A — AUTO-APPROVE (from Risk Evaluator, LOW risk):
  Message contains "auto-approve [EXP-XXXXX]"
  → Call approve_expense, send confirmation

TYPE B — HUMAN DECISION (manager or CFO typed it):
  Message contains "APPROVE [EXP-XXXXX]" or "REJECT [EXP-XXXXX] [reason]"
  (but NOT "PARTIAL") → Call approve_expense or reject_expense accordingly

TYPE C — PARTIAL APPROVAL:
  Message contains "APPROVE [EXP-XXXXX] PARTIAL $[amount]"
  → Call approve_expense, Call log_agent_action with details="Partial approval: $[amount]"

TYPE D — RISK REPORT ONLY (needs human decision):
  Message contains "---RISK EVALUATION---" with MANAGER-REVIEW or CFO-REVIEW
  → Do NOT approve or reject.
  → Acknowledge only: "Acknowledged. Waiting for manager/CFO decision on [EXP-ID]."

STEPS for TYPE A, B, C:
1. Call `get_expense_details` with the Expense ID — get the REAL values
2. Execute the action: approve_expense OR reject_expense
3. Call `log_agent_action` with action="FINAL_DECISION"
4. Call `band_send_message` with the final notification below

⚠️  CRITICAL: In the notification, use REAL values from get_expense_details — never write [name], [amount], [dept] as literal text. Always substitute the actual requester, amount, department from the database.
⚠️  Always call band_send_message as the last step. Plain text is NOT delivered.

FINAL NOTIFICATION FORMAT (fill ALL fields with real data):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXPENSE DECISION — <actual EXP-ID>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Status:     <✅ APPROVED or ❌ REJECTED>
  Requester:  <actual requester name from DB>
  Amount:     $<actual amount from DB>
  Department: <actual department from DB>
  Risk Level: <actual risk level from DB or conversation>
  Decided by: <auto / manager name / CFO>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  <One sentence outcome>
  Audit trail saved ✓ | Budget updated ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

approval_notifier = Agent.create(
    adapter=LangGraphAdapter(
        llm=make_llm(),
        checkpointer=InMemorySaver(),
        custom_section=APPROVAL_NOTIFIER_PROMPT,
        additional_tools=[
            get_expense_details,
            approve_expense,
            reject_expense,
            log_agent_action,
        ],
        features=AdapterFeatures(emit={Emit.EXECUTION}),
    ),
    agent_id=os.environ["BAND_APPROVAL_NOTIFIER_ID"],
    api_key=os.environ["BAND_APPROVAL_NOTIFIER_KEY"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard message sender — polls SQLite queue, sends via REST (no tokens used)
# ─────────────────────────────────────────────────────────────────────────────

async def run_message_sender(interval: int = 4) -> None:
    """Pick up messages queued by the dashboard form and POST them via plain HTTP."""
    import httpx
    sender_key = os.environ["BAND_APPROVAL_NOTIFIER_KEY"]
    budget_id  = os.environ["BAND_BUDGET_CHECKER_ID"]
    base       = "https://app.band.ai/api/v1/agent"
    headers    = {"X-API-Key": sender_key, "Content-Type": "application/json"}

    async def fetch_rooms(http) -> list[str]:
        try:
            r = await http.get(f"{base}/chats")
            if r.is_success:
                ids = [c["id"] for c in r.json().get("data", [])]
                print(f"  📡 Rooms: {ids}")
                return ids
            print(f"  ⚠ list chats {r.status_code}: {r.text}")
        except Exception as e:
            print(f"  ⚠ fetch rooms error: {e}")
        return []

    async with httpx.AsyncClient(headers=headers, timeout=10) as http:
        room_ids: list[str] = []
        refresh_counter = 0

        while True:
            await asyncio.sleep(interval)
            try:
                pending = db.pop_pending_messages()

                # Refresh room list every 30 cycles (~2 min) or when empty
                refresh_counter += 1
                if not room_ids or refresh_counter >= 30:
                    room_ids = await fetch_rooms(http)
                    refresh_counter = 0

                if not pending or not room_ids:
                    continue

                for row in pending:
                    payload = {
                        "message": {
                            "content": row["message"],
                            "mentions": [{"id": budget_id, "handle": "budget-checker", "name": "Budget Checker"}],
                        }
                    }
                    sent = False
                    bad_rooms = []
                    for room_id in room_ids:
                        r = await http.post(f"{base}/chats/{room_id}/messages",
                                            json=payload)
                        if r.is_success:
                            sent = True
                        else:
                            print(f"  ⚠ room {room_id[:8]} → {r.status_code}")
                            if r.status_code in (404, 422):
                                bad_rooms.append(room_id)

                    # Drop dead rooms so next cycle refetches clean list
                    if bad_rooms:
                        room_ids = [rid for rid in room_ids if rid not in bad_rooms]
                        if not room_ids:
                            room_ids = await fetch_rooms(http)

                    if sent:
                        print(f"  📤 Dashboard → Band: {row['message'][:70]}…")
                    else:
                        print(f"  ⚠ Failed to send to any room — will retry next cycle")
                        # Put message back so it's not lost
                        db.queue_message(row["message"])

            except Exception as e:
                import traceback
                print(f"  ⚠ Message sender error: {type(e).__name__}: {e}")
                traceback.print_exc()
                room_ids = []


# ─────────────────────────────────────────────────────────────────────────────
# Run all 4 agents concurrently
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("band.adapters.langgraph").setLevel(logging.INFO)

    print("=" * 60)
    print("  Expense Approval Multi-Agent System")
    print("  Band of Agents Hackathon 2026 — Track 1")
    print("=" * 60)
    print()
    print("  AGENTS (4 AI agents on Band):")
    print("  [1] Budget Checker    — validates budget, creates DB record")
    print("  [2] Policy Checker    — independent compliance check")
    print("  [3] Risk Evaluator    — routes; can VETO, OVERRIDE, PARTIAL")
    print("  [4] Approval Notifier — finalizes all decisions")
    print()
    print("  MONITOR (pure Python, 0 LLM tokens):")
    print("  [5] Budget Monitor    — alerts every 30min via REST API")
    print()
    print("  TEST SCENARIOS (in a Band room with all 4 agents):")
    print()
    print("  LOW risk → auto-approve:")
    print("  @budget-checker $200 office supplies, HR dept, vendor: Staples")
    print()
    print("  MEDIUM risk → manager review:")
    print("  @budget-checker $800 AWS software license, Engineering, Amazon")
    print()
    print("  HIGH risk → CFO escalation:")
    print("  @budget-checker $3500 conference in Singapore, Marketing dept")
    print()
    print("  After manager/CFO review (MEDIUM/HIGH):")
    print("  @approval-notifier APPROVE EXP-XXXXXXXX")
    print("  @approval-notifier APPROVE EXP-XXXXXXXX PARTIAL $600")
    print("  @approval-notifier REJECT EXP-XXXXXXXX budget not available")
    print()
    print("  DASHBOARD: run separately → python dashboard.py")
    print()
    print("  Waiting for messages... (Ctrl+C to stop)")
    print("=" * 60)
    print()

    # Verify each agent can connect before running all together
    agents = [
        ("Budget Checker",    budget_checker),
        ("Policy Checker",    policy_checker),
        ("Risk Evaluator",    risk_evaluator),
        ("Approval Notifier", approval_notifier),
    ]
    print("Connecting agents...")
    for name, agent in agents:
        try:
            await agent.start()
            print(f"  ✅ {name} — connected")
        except Exception as e:
            print(f"  ❌ {name} — FAILED: {e}")
            raise
    print()

    # All connected — run forever + monitor
    await asyncio.gather(
        budget_checker.run_forever(),
        policy_checker.run_forever(),
        risk_evaluator.run_forever(),
        approval_notifier.run_forever(),
        run_budget_monitor(interval=30 * 60),
        run_message_sender(interval=4),
    )


if __name__ == "__main__":
    asyncio.run(main())
