# AI-Powered Expense Approval System

> **Band of Agents Hackathon 2026 — Track 1: Internal Enterprise Workflows**

4 AI agents collaborate through Band to fully automate enterprise expense approvals — budget validation, policy compliance, risk scoring, and final decisions. Humans are only involved when genuinely necessary.

**Live demo:** `http://103.157.204.120:5000`

---

## Architecture

```
Employee (web form)
        │
        ▼
[Agent 1] Budget Checker  ──────────────────────────  GPT-4o / AIML API
        │
        ▼
[Agent 2] Policy Checker  ──────────────────────────  Llama 3.1 70B / Featherless AI
        │
        ▼
[Agent 3] Risk Evaluator  ──────────────────────────  GPT-4o / AIML API
        │
   ┌────┴────────────────┐
   ▼                     ▼
LOW → auto-approve    MEDIUM/HIGH → Admin Panel or Band
   │                     │
   └────────┬────────────┘
            ▼
[Agent 4] Approval Notifier ─────────────────────────  GPT-4o / AIML API
            │
     Final notification → Band room + DB
```

---

## Risk Routing

| Risk Level | Condition | Action |
|---|---|---|
| LOW | amount ≤ $500 AND COMPLIANT AND budget OK | Auto-approved in ~15 seconds |
| MEDIUM | $500 < amount ≤ $1,500 OR CONDITIONAL | Manager reviews via Admin Panel |
| HIGH | amount > $1,500 OR NON-COMPLIANT OR budget exceeded | CFO escalation |

---

## Web App (Single URL — 2 tabs)

**`http://YOUR_IP:5000`**

| Tab | Who uses it | What it does |
|---|---|---|
| **Submit Expense** | Employee | Fill form → queued → pipeline runs automatically |
| **Admin Panel** | Manager / CFO | Review pending expenses, approve/reject, live feed, budget management |

The Admin Panel includes:
- **Chờ Duyệt** — pending expenses with Approve / Reject buttons (direct DB update, no Band account needed)
- **Lịch Sử** — full expense history with status and risk level
- **Live Feed** — real-time agent activity from audit log
- **Ngân Sách** — department budget cards with one-click reset

---

## Policy Rules (checked by Llama 3.1 70B)

| Rule | Condition | Result |
|---|---|---|
| Software pre-approval | amount > $1,000 | NON-COMPLIANT |
| CFO sign-off | amount > $5,000 | NON-COMPLIANT |
| Travel notice | amount > $500 | CONDITIONAL |
| Hardware tracking | amount > $500 | CONDITIONAL |
| Flagged keywords | `personal`, `gift`, `alcohol`, `entertainment`, `casino` | NON-COMPLIANT |

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent framework | Band SDK (LangGraphAdapter + InMemorySaver) |
| LLM — 3 agents | GPT-4o via AIML API |
| LLM — Policy Checker | Llama 3.1 70B via Featherless AI |
| Agent communication | Band WebSocket + REST API |
| Web app | Flask + HTML/CSS/JS (single app, 2 tabs) |
| Database | SQLite |
| Infrastructure | Docker Compose (3 services) |
| Tunnel | Cloudflare Tunnel (optional, for public HTTPS URL) |
| Deploy | Linux VPS (24/7) |

---

## Project Structure

```
band-expense-approval-agents/
├── main.py              # 4 AI agents + message queue sender
├── app.py               # Combined web app — Submit + Admin Panel (port 5000)
├── tools.py             # LangChain tools wrapping DB operations
├── db.py                # SQLite layer (budgets, expenses, audit log, queue)
├── monitor.py           # Budget monitor (no LLM cost)
├── Dockerfile
├── docker-compose.yml   # 3 services: agents, web, tunnel-web (optional)
├── pyproject.toml
└── .env.example
```

---

## Setup

### Docker (recommended)

```bash
git clone https://github.com/thanhvuaws-jpg/band-expense-approval-agents.git
cd band-expense-approval-agents

cp .env.example .env
# Fill in API keys

docker compose up -d --build
```

App: `http://YOUR_IP:5000`

### Environment Variables

```env
BAND_BUDGET_CHECKER_ID=
BAND_BUDGET_CHECKER_KEY=

BAND_POLICY_CHECKER_ID=
BAND_POLICY_CHECKER_KEY=

BAND_RISK_EVALUATOR_ID=
BAND_RISK_EVALUATOR_KEY=

BAND_APPROVAL_NOTIFIER_ID=
BAND_APPROVAL_NOTIFIER_KEY=

AIML_API_KEY=
FEATHERLESS_API_KEY=
```

### Band Setup

1. Create a new room in Band
2. Invite all 4 agents to the room
3. Submit a test expense from the web form

---

## Demo Scenarios

### Scenario 1 — LOW Risk (auto-approved, ~15 seconds)

Submit: `$200, HR, Staples, "office supplies"`

```
Budget OK → COMPLIANT → LOW → ✅ Auto-approved
```

### Scenario 2 — MEDIUM Risk (manager review)

Submit: `$800, Engineering, Amazon, "AWS software license"`

```
Budget OK → COMPLIANT → MEDIUM → ⚠️ Admin Panel / Band
Manager clicks Approve → ✅ APPROVED
```

### Scenario 3 — HIGH Risk (CFO escalation)

Submit: `$6000, Finance, SAP, "SAP ERP license"`

```
Budget OK → NON-COMPLIANT (>$5,000) → HIGH → 🚨 CFO escalation
Admin Panel / Band: Reject with reason → ❌ REJECTED
```

---

## Services (docker-compose)

| Service | Description | Port |
|---|---|---|
| `agents` | 4 AI agents + message sender | — |
| `web` | Flask web app (Submit + Admin Panel) | 5000 |
| `tunnel-web` | Cloudflare Tunnel (public HTTPS URL) | — |

---

Built for **Band of Agents Hackathon 2026** · Track 1: Internal Enterprise Workflows

Powered by **Band SDK** · **AIML API (GPT-4o)** · **Featherless AI (Llama 3.1 70B)**
