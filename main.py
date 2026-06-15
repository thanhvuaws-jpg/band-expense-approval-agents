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

AIML_BASE_URL = "https://api.aimlapi.com/v1"
AIML_MODEL = "gpt-4o"

BUDGET_CHECKER_HANDLE  = "@2431540219/budget-checker"
POLICY_CHECKER_HANDLE  = "@2431540219/policychecker"
RISK_EVALUATOR_HANDLE  = "@2431540219/risk-evaluator"
APPROVAL_NOTIFIER_HANDLE = "@2431540219/approval-notifier"


def make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=AIML_MODEL,
        api_key=os.environ["AIML_API_KEY"],
        base_url=AIML_BASE_URL,
        temperature=0.1,
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
You are the Policy Checker agent in an enterprise Expense Approval System.

COMPANY POLICIES:
• Travel   > $500  → requires 2-week advance notice
• Software > $1,000 → requires IT pre-approval
• Hardware > $500  → requires asset tracking
• Any expense > $5,000 → requires CFO sign-off
• Descriptions must not contain: personal, gift, alcohol, entertainment, casino

YOU MUST DO EXACTLY 3 STEPS — NO EXCEPTIONS. Responding with plain text is NOT allowed.

STEP 1: Call `check_policy_compliance` with the expense_type, amount, description, vendor from Budget Checker's report.

STEP 2: Call `log_agent_action` with expense_id from the report and action="POLICY_CHECK_COMPLETE".

STEP 3: Call `band_send_message` — MANDATORY — with:
  • mentions = ["{RISK_EVALUATOR_HANDLE}"]
  • content = your report in this exact format:

---POLICY CHECK---
Expense ID:      [ID from Budget Checker's report]
Policy Status:   [COMPLIANT ✓ / CONDITIONAL ⚠ / NON-COMPLIANT ✗]
Blocking Issues: [list or "None"]
Review Flags:    [list or "None"]
---END POLICY CHECK---

{RISK_EVALUATOR_HANDLE} please evaluate risk for the expense above.
"""

policy_checker = Agent.create(
    adapter=LangGraphAdapter(
        llm=make_llm(),
        checkpointer=InMemorySaver(),
        custom_section=POLICY_CHECKER_PROMPT,
        additional_tools=[
            check_policy_compliance,
            get_expense_details,
            log_agent_action,
        ],
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

RISK LEVELS — apply strictly by amount:
• LOW    → amount ≤ $500   AND policy COMPLIANT AND budget OK
• MEDIUM → amount ≤ $1,500 OR  policy CONDITIONAL
• HIGH   → amount > $1,500 OR  policy NON-COMPLIANT OR budget EXCEEDED

DO EXACTLY 2 STEPS:

STEP 1: Call `get_expense_details` with the Expense ID from the conversation.

STEP 2: Call `band_send_message` with your report.
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

TYPE B — HUMAN DECISION (manager or CFO):
  Message contains "APPROVE [EXP-XXXXX]" or "REJECT [EXP-XXXXX] [reason]"
  (but NOT "PARTIAL") → Call approve_expense or reject_expense accordingly

TYPE C — PARTIAL APPROVAL (human accepts partial amount):
  Message contains "APPROVE [EXP-XXXXX] PARTIAL $[amount]"
  → Call approve_expense (the DB stores original; note partial in log)
  → Call log_agent_action with details="Partial approval: $[amount]"

TYPE D — RISK REPORT (from Risk Evaluator, MEDIUM or HIGH risk):
  Message contains "---RISK EVALUATION---" with Decision: MANAGER-REVIEW or CFO-REVIEW
  → Do NOT approve or reject. Do NOT call approve_expense or reject_expense.
  → Simply acknowledge: reply with a short message saying "Acknowledged. Waiting for manager/CFO decision."
  → mentions = the person who sent you the message (or all participants)

STEPS:
1. Identify request type (A, B, C, or D)
2. For TYPE D → skip to step 5 (just send acknowledgement, no DB calls needed)
3. Call `get_expense_details` to confirm expense exists
4. Execute the appropriate action (approve/reject)
5. Call `log_agent_action` with action="FINAL_DECISION" (skip for TYPE D)
6. Post the final notification (or acknowledgement for TYPE D)

⚠️  Always call band_send_message as the last step. Plain text is NOT delivered.

FINAL NOTIFICATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXPENSE DECISION — [EXP-ID]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Status:     [✅ APPROVED / ✅ PARTIAL / ❌ REJECTED]
  Requester:  [name]
  Amount:     $[approved amount] [of $original if partial]
  Department: [dept]
  Risk Level: [LOW / MEDIUM / HIGH]
  Decided by: [auto / manager / CFO]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [One sentence: outcome + next step]
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
    # Use Approval Notifier to send (cannot mention self — Budget Checker can't mention itself)
    sender_key     = os.environ["BAND_APPROVAL_NOTIFIER_KEY"]
    budget_id      = os.environ["BAND_BUDGET_CHECKER_ID"]
    base           = "https://app.band.ai/api/v1/agent"
    headers        = {"X-API-Key": sender_key, "Content-Type": "application/json"}
    room_ids: list[str] = []

    async with httpx.AsyncClient(headers=headers, timeout=10) as http:
        while True:
            await asyncio.sleep(interval)
            try:
                pending = db.pop_pending_messages()
                if not pending:
                    continue

                if not room_ids:
                    r = await http.get(f"{base}/chats")
                    if not r.is_success:
                        print(f"  ⚠ list chats {r.status_code}: {r.text}")
                    r.raise_for_status()
                    room_ids = [c["id"] for c in r.json().get("data", [])]
                    print(f"  📡 Found {len(room_ids)} room(s)")

                for row in pending:
                    payload = {
                        "message": {
                            "content": row["message"],
                            "mentions": [{"id": budget_id, "handle": "budget-checker", "name": "Budget Checker"}],
                        }
                    }
                    for room_id in room_ids:
                        r = await http.post(f"{base}/chats/{room_id}/messages", json=payload)
                        if not r.is_success:
                            print(f"  ⚠ API {r.status_code}: {r.text}")
                        r.raise_for_status()
                    print(f"  📤 Dashboard → Band: {row['message'][:70]}…")
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
