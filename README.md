# Expense Approval Multi-Agent System

> **Band of Agents Hackathon 2026 — Track 1: Internal Enterprise Workflows**

A production-grade multi-agent expense approval system built on [Band](https://band.ai). Four specialized AI agents collaborate in real-time through Band's shared communication layer — passing structured context, making independent decisions, escalating to humans, and completing a full enterprise approval workflow autonomously.

---

## Mục lục / Table of Contents

- [Tổng quan / Overview](#tổng-quan--overview)
- [Kiến trúc / Architecture](#kiến-trúc--architecture)
- [Các Agent / Agents](#các-agent--agents)
- [Con người trong quy trình / Human-in-the-Loop](#con-người-trong-quy-trình--human-in-the-loop)
- [Tại sao đây là Agent thật / Why These Are Real Agents](#tại-sao-đây-là-agent-thật--why-these-are-real-agents)
- [Tech Stack](#tech-stack)
- [Cài đặt / Setup](#cài-đặt--setup)
- [Chạy thử / Running](#chạy-thử--running)
- [Kịch bản demo / Demo Scenarios](#kịch-bản-demo--demo-scenarios)

---

## Tổng quan / Overview

**Tiếng Việt:**
Hệ thống tự động xử lý yêu cầu chi phí trong doanh nghiệp thông qua 4 AI agent chuyên biệt hoạt động song song qua Band. Mỗi agent đóng một vai trò độc lập, trao đổi kết quả có cấu trúc, và leo thang quyết định đến con người khi cần thiết.

**English:**
An automated expense approval pipeline where four specialized AI agents coordinate through Band's shared environment. Each agent plays an independent role — validating budgets, checking compliance, evaluating risk, and finalizing decisions — while escalating to human managers or CFOs for high-stakes approvals.

---

## Kiến trúc / Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BAND SHARED ROOM                                  │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │   Dashboard  │    │  Band Chat   │    │   Manager /  │           │
│  │   (Web UI)   │    │  (Direct)    │    │     CFO      │           │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘           │
│         │                  │                    │                    │
│         └──────────────────▼────────────────────┘                   │
│                            │ Expense Request                         │
│                            ▼                                         │
│              ┌─────────────────────────┐                            │
│              │    Budget Checker [1]   │  ← Agent 1                 │
│              │  • Parse request        │                            │
│              │  • Check dept budget    │                            │
│              │  • Create DB record     │                            │
│              │  • Classify expense     │                            │
│              └─────────────┬───────────┘                            │
│                            │ @policychecker                          │
│                            ▼                                         │
│              ┌─────────────────────────┐                            │
│              │   Policy Checker [2]    │  ← Agent 2                 │
│              │  • Check IT approval    │                            │
│              │  • Check CFO threshold  │                            │
│              │  • Flag advance notice  │                            │
│              │  • Detect banned terms  │                            │
│              └─────────────┬───────────┘                            │
│                            │ @risk-evaluator                         │
│                            ▼                                         │
│              ┌─────────────────────────┐                            │
│              │   Risk Evaluator [3]    │  ← Agent 3 (decision hub)  │
│              │  • Read both reports    │                            │
│              │  • Compute risk level   │                            │
│              │  • Route to outcome     │                            │
│              └──────┬────────┬─────────┘                            │
│                     │        │                                       │
│           LOW ──────┘        └───── MEDIUM / HIGH                   │
│             │                              │                         │
│             ▼                              ▼                         │
│  ┌──────────────────┐         ┌────────────────────────┐            │
│  │ Approval         │         │  👤 Human Manager/CFO  │            │
│  │ Notifier [4]     │  ◄──────│  types APPROVE/REJECT  │            │
│  │ auto-approve     │         └────────────────────────┘            │
│  └──────────────────┘                                               │
│             │                                                        │
│             ▼                                                        │
│    ✅ Final Decision posted to room                                  │
│    Database updated | Budget deducted | Audit trail saved            │
└─────────────────────────────────────────────────────────────────────┘
```

### Luồng dữ liệu / Data Flow

```
Expense Request
      │
      ├─► Budget Checker
      │       └─► SQLite: CREATE expense record
      │       └─► SQLite: READ department budget
      │       └─► Band: SEND structured report → @policychecker
      │
      ├─► Policy Checker (receives Budget Check report via Band)
      │       └─► SQLite: READ policy rules
      │       └─► Band: SEND compliance report → @risk-evaluator
      │
      ├─► Risk Evaluator (receives both reports via Band history)
      │       └─► SQLite: READ full expense record
      │       └─► Decision: LOW / MEDIUM / HIGH
      │       └─► Band: SEND risk report → @approval-notifier
      │
      └─► Approval Notifier
              ├─► LOW:    SQLite: APPROVE + deduct budget → Band: notify
              ├─► MEDIUM: Band: notify manager → wait for human reply
              └─► HIGH:   Band: notify CFO → wait for human reply
```

---

## Các Agent / Agents

### Agent 1 — Budget Checker

**Vai trò / Role:** Điểm đầu vào — parse yêu cầu, kiểm tra ngân sách, tạo record  
**Role:** Entry point — parse the expense request, verify department budget, create the database record

| | |
|---|---|
| **Tools** | `create_expense_record`, `check_department_budget`, `get_all_department_budgets`, `log_agent_action` |
| **Input** | Natural language expense request (e.g. `$800 AWS license, Engineering, vendor: Amazon`) |
| **Output** | Structured `---BUDGET CHECK---` report forwarded to Policy Checker via Band mention |
| **Decision** | Budget status: OK ✓ / TIGHT ⚠ / EXCEEDED ✗ |

**Example output in Band:**
```
---BUDGET CHECK---
Expense ID:  EXP-A1B2C3D4
Requester:   John Smith
Amount:      $800
Department:  Engineering
Type:        software
Vendor:      Amazon
Budget Left: $6,900 (OK ✓)
---END BUDGET CHECK---
```

---

### Agent 2 — Policy Checker

**Vai trò / Role:** Chuyên gia compliance độc lập — kiểm tra theo đúng policy của công ty  
**Role:** Independent compliance specialist — verifies against company policy rules

| | |
|---|---|
| **Tools** | `check_policy_compliance`, `get_expense_details`, `log_agent_action` |
| **Policy Rules** | Travel >$500 → 2-week advance notice; Software >$1,000 → IT pre-approval; Any expense >$5,000 → CFO sign-off; Flagged terms: personal, gift, alcohol, casino |
| **Input** | Budget Checker's report (via Band history) |
| **Output** | Structured `---POLICY CHECK---` report forwarded to Risk Evaluator |
| **Decision** | COMPLIANT ✓ / CONDITIONAL ⚠ / NON-COMPLIANT ✗ |

---

### Agent 3 — Risk Evaluator

**Vai trò / Role:** Bộ não ra quyết định — đọc cả 2 báo cáo, tính risk, route đến đúng nơi  
**Role:** Decision hub — reads both reports, computes risk level, routes to the correct outcome

| | |
|---|---|
| **Tools** | `get_expense_details` |
| **Risk Logic** | LOW: ≤$500 + COMPLIANT + budget OK → auto-approve; MEDIUM: ≤$1,500 or CONDITIONAL → manager review; HIGH: >$1,500 or NON-COMPLIANT or budget EXCEEDED → CFO escalation |
| **Input** | Both Budget Check + Policy Check reports (from Band room history) |
| **Output** | Risk report + routing instruction → @approval-notifier |
| **Special** | Can read history of prior failed checks to VETO and request re-check |

---

### Agent 4 — Approval Notifier

**Vai trò / Role:** Bộ phận hoàn tất — xử lý quyết định cuối cùng và cập nhật hệ thống  
**Role:** Finalizer — handles final decisions (auto or human), updates database, posts professional notification

| | |
|---|---|
| **Tools** | `get_expense_details`, `approve_expense`, `reject_expense`, `log_agent_action` |
| **Input types** | A: "auto-approve [ID]" from Risk Evaluator; B: "APPROVE/REJECT [ID]" from human; C: "APPROVE [ID] PARTIAL $X" for partial approval; D: MEDIUM/HIGH risk report (acknowledge + wait) |
| **On APPROVE** | Calls `approve_expense` → deducts from department budget → posts decision |
| **On REJECT** | Calls `reject_expense` → no budget change → posts decision with reason |

---

## Con người trong quy trình / Human-in-the-Loop

Đây là điểm quan trọng nhất về thiết kế: **AI xử lý tự động khi an toàn, và giao cho con người khi rủi ro cao**.

The key design principle: **AI handles what is safe to automate, humans decide when stakes are high.**

```
Risk Level   Who decides?          How?
──────────   ─────────────────     ──────────────────────────────────────────
LOW          AI (auto)             Approval Notifier approves automatically
MEDIUM       Human Manager         Types in Band: @approval-notifier APPROVE EXP-XXXX
HIGH         CFO                   Types in Band: @approval-notifier APPROVE EXP-XXXX
                                   or: @approval-notifier REJECT EXP-XXXX [reason]
```

**Con người tham gia tại đây / Humans are in the loop here:**

1. **Gửi yêu cầu / Submit request** — Human submits expense via Dashboard (web form) or directly in Band chat
2. **Quyết định MEDIUM / MEDIUM approval** — Human manager reads Risk Evaluator's report in Band and types APPROVE or REJECT
3. **Quyết định HIGH / HIGH approval** — CFO reads the escalation in Band and types APPROVE or REJECT
4. **Kết quả tức thì / Immediate result** — Approval Notifier processes the human's decision immediately and updates the database

The system never auto-approves MEDIUM or HIGH risk expenses. Human judgment is always required for anything non-trivial.

---

## Tại sao đây là Agent thật / Why These Are Real Agents

Điều phân biệt hệ thống này với một chatbot hay automation script thông thường:

What distinguishes this from a chatbot or simple automation script:

### 1. Autonomous Tool Use / Sử dụng tool tự chủ
Each agent independently decides which tools to call, in which order, with which parameters. The LLM reasons about the task and selects tools — no hardcoded call sequence.

### 2. Structured Context Passing / Truyền context có cấu trúc
Agents exchange structured, machine-readable reports through Band. Each downstream agent reads the upstream report and extracts the information it needs. This is real agent-to-agent communication, not just sequential function calls.

### 3. Shared State via Band Room / Trạng thái chung qua Band Room
All agents operate in the same Band room. Risk Evaluator reads the FULL history — both Budget Check AND Policy Check — before making its decision. Context accumulates and is available to all agents.

### 4. Independent Decision-Making / Ra quyết định độc lập
Risk Evaluator makes routing decisions (LOW/MEDIUM/HIGH) based on multi-factor analysis. Policy Checker independently evaluates compliance without knowing what Risk Evaluator will decide. Each agent has its own reasoning.

### 5. Non-linear Escalation / Leo thang phi tuyến
The workflow is NOT a simple A→B→C chain. Risk Evaluator can VETO and send back to Budget Checker. Humans can inject decisions at any point. The pipeline adapts to the situation.

### 6. Real Persistent State / Trạng thái tồn tại thật
Every agent action writes to SQLite. Budget deductions are permanent. Audit trails are immutable. The system has real state, not just in-memory conversation.

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | [Band SDK](https://band.ai) + [LangGraph](https://github.com/langchain-ai/langgraph) ReAct |
| LLM | GPT-4o via [AI/ML API](https://aimlapi.com) |
| Agent Communication | Band (Phoenix Channels WebSocket + REST API) |
| Database | SQLite (budgets, expenses, audit trail) |
| Dashboard | Flask + HTML/CSS/JS |
| Budget Monitor | Pure Python (zero LLM cost) |

```
band-sdk            → agent runtime, WebSocket, mentions, message routing
langgraph           → ReAct agent loop (think → tool → observe → repeat)
langchain-openai    → LLM interface
sqlite3             → persistent state
flask               → web dashboard
httpx               → REST API calls
```

---

## Cài đặt / Setup

### Prerequisites
- Python 3.11+
- Band account with 4 agents created at [band.ai](https://band.ai)
- AI/ML API key from [aimlapi.com](https://aimlapi.com)

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/band-expense-approval-agents.git
cd band-expense-approval-agents

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Band agent credentials (create 4 agents at band.ai)
BAND_BUDGET_CHECKER_ID=your-agent-id
BAND_BUDGET_CHECKER_KEY=band_a_...

BAND_POLICY_CHECKER_ID=your-agent-id
BAND_POLICY_CHECKER_KEY=band_a_...

BAND_RISK_EVALUATOR_ID=your-agent-id
BAND_RISK_EVALUATOR_KEY=band_a_...

BAND_APPROVAL_NOTIFIER_ID=your-agent-id
BAND_APPROVAL_NOTIFIER_KEY=band_a_...

# AI/ML API (https://aimlapi.com)
AIML_API_KEY=your-key-here
```

### 3. Add all 4 agents to a Band room

Create a Band room and invite all 4 agents. The system uses one shared room for all agent communication.

---

## Chạy thử / Running

### Quick Start (recommended)

Double-click `start.bat` (Windows) — opens 2 terminals automatically:
- Terminal 1: AI agents (`main.py`)
- Terminal 2: Dashboard UI (`dashboard.py`)

### Manual

**Terminal 1 — AI Agents:**
```bash
python main.py
```

**Terminal 2 — Dashboard:**
```bash
python dashboard.py
# → http://localhost:5000
```

---

## Kịch bản demo / Demo Scenarios

### Scenario 1 — LOW Risk (Auto-approved) ✅

Type in Band or submit via dashboard:
```
@budget-checker $200 office supplies, HR dept, vendor: Staples
```

**Flow:**
1. Budget Checker → budget OK, creates EXP-XXXXXX
2. Policy Checker → COMPLIANT (no flags)
3. Risk Evaluator → LOW ($200 ≤ $500, compliant)
4. Approval Notifier → **auto-approves**, deducts $200 from HR budget

**No human needed.** Full pipeline runs in ~20 seconds.

---

### Scenario 2 — MEDIUM Risk (Manager Review) ⚠️

```
@budget-checker $800 conference tickets, Marketing dept, vendor: Eventbrite
```

**Flow:**
1. Budget Checker → creates record
2. Policy Checker → CONDITIONAL (travel >$500 needs 2-week notice)
3. Risk Evaluator → MEDIUM → requests manager decision
4. **Human manager types:** `@approval-notifier APPROVE EXP-XXXXXX`
5. Approval Notifier → approved by manager, budget updated

---

### Scenario 3 — HIGH Risk (CFO Escalation) 🚨

```
@budget-checker $6000 executive software license, Engineering dept, vendor: SAP
```

**Flow:**
1. Budget Checker → creates record
2. Policy Checker → NON-COMPLIANT (software >$1,000 needs IT pre-approval, >$5,000 needs CFO)
3. Risk Evaluator → HIGH → CFO escalation
4. **CFO types:** `@approval-notifier APPROVE EXP-XXXXXX`
   or: `@approval-notifier REJECT EXP-XXXXXX budget not available this quarter`
5. Approval Notifier → final decision with full audit trail

---

### Scenario 4 — Dashboard Submission 🖥️

Open `http://localhost:5000`, fill in the form:
- Requester name, amount, department, description, vendor
- Click **Submit**

The system automatically routes through all 4 agents. No Band chat needed for submission — only for MEDIUM/HIGH approval decisions.

---

## Cấu trúc project / Project Structure

```
.
├── main.py          # 4 agents + message sender + startup
├── dashboard.py     # Flask web UI for expense submission
├── tools.py         # LangChain tools wrapping the database
├── db.py            # SQLite layer (budgets, expenses, audit)
├── monitor.py       # Budget monitor (no LLM, pure Python)
├── start.bat        # One-click launcher (Windows)
├── pyproject.toml   # Dependencies
└── .env.example     # Environment variable template
```

---

## License

MIT
