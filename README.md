# AI-Powered Expense Approval System

> **Band of Agents Hackathon 2026 — Track 1: Internal Enterprise Workflows**

Hệ thống duyệt chi phí doanh nghiệp tự động, sử dụng 4 AI agent chuyên biệt phối hợp qua Band. Pipeline xử lý từ đầu đến cuối — kiểm tra ngân sách, compliance, đánh giá rủi ro, và ra quyết định cuối cùng — chỉ leo thang đến con người khi thực sự cần thiết.

An enterprise expense approval system powered by 4 specialized AI agents collaborating through Band. The pipeline handles everything end-to-end — budget validation, compliance checking, risk evaluation, and final decisions — escalating to humans only when genuinely necessary.

---

## Mục lục / Table of Contents

- [Vấn đề & Giải pháp](#1-vấn-đề--giải-pháp)
- [Tác nhân sử dụng](#2-tác-nhân-sử-dụng--stakeholders)
- [Kiến trúc hệ thống](#3-kiến-trúc-hệ-thống--architecture)
- [Sơ đồ luồng xử lý](#4-sơ-đồ-luồng-xử-lý--flow-diagrams)
- [Chi tiết 4 AI Agent](#5-chi-tiết-4-ai-agent)
- [Human-in-the-Loop](#6-human-in-the-loop)
- [Tech Stack](#7-tech-stack)
- [Cài đặt & Chạy](#8-cài-đặt--chạy--setup--running)
- [Demo Scenarios](#9-demo-scenarios)
- [Scale lên Enterprise](#10-scale-lên-enterprise)
- [Cấu trúc Project](#11-cấu-trúc-project)

---

## 1. Vấn đề & Giải pháp

### Vấn đề thực tế

Trong doanh nghiệp, quy trình duyệt chi phí thủ công gặp nhiều bất cập:

- Mất **2–3 ngày** xử lý mỗi yêu cầu do phải chuyền tay qua nhiều phòng ban
- Manager phải duyệt **cả những khoản nhỏ** không cần thiết, lãng phí thời gian
- Dễ **sai sót**: nhầm ngân sách, bỏ qua quy định policy
- Không có **audit trail** rõ ràng khi xảy ra tranh chấp
- Không có **cảnh báo sớm** khi ngân sách sắp cạn

### Giải pháp

4 AI agent chuyên biệt phối hợp tự động qua Band:

| Trước (Thủ công) | Sau (AI Agent) |
|---|---|
| 2–3 ngày xử lý | ~30 giây (LOW risk) |
| Manager duyệt tất cả | Chỉ leo thang khi cần |
| Dễ quên quy định | Policy check tự động 100% |
| Không có audit trail | Mọi hành động đều được ghi lại |
| Không biết ngân sách còn bao nhiêu | Real-time budget tracking |

---

## 2. Tác nhân sử dụng / Stakeholders

| Tác Nhân | Vai Trò | Công Cụ | Tần Suất |
|---|---|---|---|
| **Nhân viên** | Gửi yêu cầu chi phí, theo dõi kết quả | Web Dashboard | Hàng ngày |
| **Manager** | Duyệt/từ chối chi phí rủi ro MEDIUM | Band | Khi có thông báo |
| **CFO** | Duyệt/từ chối chi phí rủi ro HIGH (>$1,500) | Band | Khi có leo thang |
| **IT Admin** | Cài đặt và vận hành hệ thống | VPS + Docker | Setup 1 lần |
| **4 AI Agents** | Xử lý pipeline tự động 24/7 | Band SDK + LLM | Tức thì |

---

## 3. Kiến trúc hệ thống / Architecture

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION LAYER                            │
│                                                                     │
│   ┌─────────────────────┐          ┌──────────────────────────┐    │
│   │    Web Dashboard     │          │        Band App           │    │
│   │  (Nhân viên submit) │          │  (Manager / CFO duyệt)   │    │
│   │   http://server:5000│          │    gõ APPROVE / REJECT    │    │
│   └──────────┬──────────┘          └─────────────┬────────────┘    │
└──────────────┼─────────────────────────────────────┼────────────────┘
               │ HTTP POST                           │ WebSocket
┌──────────────▼─────────────────────────────────────▼────────────────┐
│                        AI AGENT LAYER                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │
│  │   Budget     │  │   Policy     │  │    Risk      │  │Approval│ │
│  │   Checker    │─▶│   Checker    │─▶│  Evaluator   │─▶│Notifier│ │
│  │  [GPT-4o]    │  │[Llama 3.1]  │  │  [GPT-4o]    │  │[GPT-4o]│ │
│  │  AIML API    │  │ Featherless  │  │  AIML API    │  │AIML API│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────┘ │
│                                                                     │
│                  Band SDK + LangGraph ReAct Loop                   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ SQLite / PostgreSQL
┌─────────────────────────────────▼───────────────────────────────────┐
│                          DATA LAYER                                 │
│                                                                     │
│    budgets  │  expenses  │  audit_log  │  pending_sends             │
│   (ngân sách) (chi phí)  (nhật ký)    (queue web→Band)             │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Communication Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                       BAND SHARED ROOM                           │
│                                                                  │
│   Nhân Viên ──────────────────────────────────────────────────  │
│       │  @budget-checker $200 office supplies, HR dept          │
│       │                                                          │
│       ▼                                                          │
│   Budget Checker [1]                                             │
│       │  • Kiểm tra ngân sách Engineering: $2,500 còn lại       │
│       │  • Tạo record EXP-XXXXXXXX trong SQLite                 │
│       │  @policychecker ---BUDGET CHECK--- ...                   │
│       │                                                          │
│       ▼                                                          │
│   Policy Checker [2]  (Featherless AI - Llama 3.1 70B)          │
│       │  • Kiểm tra: software >$1000? travel >$500? CFO?        │
│       │  • Kết quả: COMPLIANT / CONDITIONAL / NON-COMPLIANT     │
│       │  @risk-evaluator POLICY CHECK | Status: COMPLIANT       │
│       │                                                          │
│       ▼                                                          │
│   Risk Evaluator [3]                                             │
│       │  • Đọc cả 2 báo cáo Budget + Policy                     │
│       │  • Phân loại: LOW / MEDIUM / HIGH                        │
│       │                                                          │
│       ├── LOW ──────▶ @approval-notifier auto-approve EXP-XXX   │
│       ├── MEDIUM ──▶ ⚠️ MANAGER REVIEW NEEDED                   │
│       └── HIGH ────▶ 🚨 CFO ESCALATION                          │
│                                                                  │
│       ▼ (sau khi human APPROVE/REJECT)                           │
│   Approval Notifier [4]                                          │
│       │  • approve_expense → deduct budget                       │
│       │  • Ghi audit trail                                       │
│       └─▶ @NhânViên ✅ APPROVED / ❌ REJECTED                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Sơ đồ luồng xử lý / Flow Diagrams

### 4.1 Sơ đồ tuần tự — LOW Risk ($200)

```
NhânViên      BudgetChecker    PolicyChecker    RiskEvaluator    ApprovalNotifier
    │               │                │                │                │
    │─$200 req ────▶│                │                │                │
    │               │─check_budget──▶                 │                │
    │               │◀─OK $2,600 ───│                 │                │
    │               │─create_expense▶                 │                │
    │               │─@policychecker▶                 │                │
    │               │                │─check_policy   │                │
    │               │                │◀─COMPLIANT ────│                │
    │               │                │─@risk-eval ──────────────────▶  │
    │               │                │                │─get_expense     │
    │               │                │                │◀─$200 OK ──────│
    │               │                │                │─AUTO-APPROVE──▶ │
    │               │                │                │                │─approve_expense
    │               │                │                │                │─deduct_budget
    │◀──────────────────────────────────────────── ✅ APPROVED ────────│
    │  (~30 giây, không cần con người)                                  │
```

### 4.2 Sơ đồ tuần tự — MEDIUM Risk ($800)

```
NhânViên      BudgetChecker    PolicyChecker    RiskEvaluator    ApprovalNotifier   Manager
    │               │                │                │                │               │
    │─$800 req ────▶│                │                │                │               │
    │               │─────────────── pipeline ───────▶                │               │
    │               │                │                │─MANAGER-REVIEW▶               │
    │               │                │                │                │─⚠️ MANAGER──▶ │
    │               │                │                │                │               │
    │               │                │                │                │◀─APPROVE ─────│
    │               │                │                │                │─approve_db     │
    │◀──────────────────────────────────────────── ✅ APPROVED ────────│               │
```

### 4.3 Sơ đồ tuần tự — HIGH Risk ($6,000)

```
NhânViên      BudgetChecker    PolicyChecker    RiskEvaluator    ApprovalNotifier    CFO
    │               │                │                │                │               │
    │─$6000 req────▶│                │                │                │               │
    │               │─────────────── pipeline ───────▶                │               │
    │               │                │─NON-COMPLIANT ▶                │               │
    │               │                │                │─CFO-REVIEW ──▶ │               │
    │               │                │                │                │─🚨 CFO ──────▶│
    │               │                │                │                │               │
    │               │                │                │                │◀─REJECT ──────│
    │               │                │                │                │─reject_db      │
    │◀──────────────────────────────────────────── ❌ REJECTED ────────│               │
```

---

## 5. Chi tiết 4 AI Agent

### Agent 1 — Budget Checker
**Model:** GPT-4o via AI/ML API

Điểm đầu vào của pipeline. Nhận yêu cầu bằng ngôn ngữ tự nhiên, phân tích, kiểm tra ngân sách, tạo database record.

| | |
|---|---|
| **Tools** | `create_expense_record`, `check_department_budget`, `log_agent_action` |
| **Input** | Ngôn ngữ tự nhiên: `$800 AWS software, Engineering, vendor: Amazon` |
| **Output** | Báo cáo có cấu trúc → gửi @policychecker qua Band |

```
---BUDGET CHECK---
Expense ID:  EXP-A1B2C3D4
Requester:   Nguyen Van A
Amount:      $800
Department:  Engineering
Type:        software
Vendor:      Amazon
Budget Left: $6,900 (OK ✓)
---END BUDGET CHECK---
```

---

### Agent 2 — Policy Checker
**Model:** Llama 3.1 70B via Featherless AI

Chuyên gia compliance độc lập. Kiểm tra các quy định nội bộ và gửi kết quả đến Risk Evaluator.

| | |
|---|---|
| **Tools** | `check_policy_compliance` |
| **Input** | Budget Check report từ Band room |
| **Output** | `POLICY CHECK | Expense ID: ... | Status: COMPLIANT | Blocking: None` |

**Policy rules được kiểm tra:**
- Software > $1,000 → cần IT pre-approval
- Bất kỳ chi phí > $5,000 → cần CFO ký duyệt
- Travel > $500 → cần báo trước 2 tuần
- Hardware > $500 → cần theo dõi asset
- Từ khoá bị cấm: `personal`, `gift`, `alcohol`, `entertainment`, `casino`

---

### Agent 3 — Risk Evaluator
**Model:** GPT-4o via AI/ML API

Bộ não ra quyết định. Đọc cả hai báo cáo từ lịch sử Band room và routing đến kết quả phù hợp.

| | |
|---|---|
| **Tools** | `get_expense_details` |
| **Input** | Toàn bộ lịch sử Band room (Budget + Policy reports) |
| **Output** | Risk report + routing instruction |

**Risk logic:**
```
LOW    → amount ≤ $500   AND COMPLIANT AND budget OK  → Auto-approve
MEDIUM → amount ≤ $1,500 OR  CONDITIONAL              → Manager review
HIGH   → amount > $1,500 OR  NON-COMPLIANT OR exceeded → CFO escalation
```

---

### Agent 4 — Approval Notifier
**Model:** GPT-4o via AI/ML API

Bộ phận hoàn tất. Xử lý mọi quyết định (tự động hoặc từ con người), cập nhật database, thông báo kết quả.

| | |
|---|---|
| **Tools** | `get_expense_details`, `approve_expense`, `reject_expense`, `log_agent_action` |
| **Input types** | A: auto-approve từ Risk Evaluator; B: APPROVE/REJECT từ human; C: Partial approval |

---

## 6. Human-in-the-Loop

**Thiết kế cốt lõi:** AI xử lý tự động khi an toàn, giao con người khi rủi ro cao.

```
Risk Level        Ai quyết định?        Thời gian          Cách thực hiện
──────────────    ──────────────────    ─────────────      ─────────────────────────────────
LOW (≤$500)       AI Tự Động            ~30 giây           Không cần người
MEDIUM ($500–$1,500)  Human Manager     Manager quyết định  @approval-notifier APPROVE EXP-XXX
HIGH (>$1,500)    CFO                   CFO quyết định     @approval-notifier APPROVE EXP-XXX
                                                           @approval-notifier REJECT EXP-XXX [lý do]
```

**Con người không cần biết gì về kỹ thuật** — chỉ cần đọc báo cáo trong Band và gõ lệnh đơn giản.

---

## 7. Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | Band SDK + LangGraph ReAct |
| LLM (Budget, Risk, Approval) | GPT-4o via AI/ML API |
| LLM (Policy Checker) | Llama 3.1 70B via Featherless AI |
| Agent Communication | Band (WebSocket + REST API) |
| Database | SQLite (demo) → PostgreSQL (production) |
| Web Dashboard | Flask + HTML/CSS/JS |
| Infrastructure | Docker + Docker Compose |
| Deploy | Linux VPS (24/7) |

---

## 8. Cài đặt & Chạy / Setup & Running

### Option A — Docker (Recommended, VPS)

```bash
git clone https://github.com/thanhvuaws-jpg/band-expense-approval-agents.git
cd band-expense-approval-agents

cp .env.example .env
nano .env          # điền API keys

docker compose up -d --build
```

Dashboard: `http://YOUR_IP:5000`

### Option B — Local (Windows)

```bash
git clone https://github.com/thanhvuaws-jpg/band-expense-approval-agents.git
cd band-expense-approval-agents

python -m venv .venv
.venv\Scripts\activate
pip install -e .

cp .env.example .env
# điền .env với API keys của bạn

start.bat    # mở 2 terminal tự động
```

### .env format

```env
BAND_BUDGET_CHECKER_ID=your-agent-id
BAND_BUDGET_CHECKER_KEY=band_a_...

BAND_POLICY_CHECKER_ID=your-agent-id
BAND_POLICY_CHECKER_KEY=band_a_...

BAND_RISK_EVALUATOR_ID=your-agent-id
BAND_RISK_EVALUATOR_KEY=band_a_...

BAND_APPROVAL_NOTIFIER_ID=your-agent-id
BAND_APPROVAL_NOTIFIER_KEY=band_a_...

AIML_API_KEY=your-aiml-key
FEATHERLESS_API_KEY=your-featherless-key
```

### Bước cuối — Tạo Band room

1. Tạo room mới trên Band
2. Invite cả 4 agent vào room
3. Test bằng cách gõ lệnh trong room

---

## 9. Demo Scenarios

### Scenario 1 — LOW Risk ✅ (Auto-approved ~30 giây)

```
@budget-checker $200 office supplies, HR dept, vendor: Staples
```

Pipeline: Budget OK → COMPLIANT → LOW → **Auto-approved, $200 deducted từ HR budget**

---

### Scenario 2 — MEDIUM Risk ⚠️ (Manager duyệt)

```
@budget-checker $800 conference tickets, Marketing dept, vendor: Eventbrite
```

Pipeline: Budget OK → CONDITIONAL → MEDIUM → **Manager nhận thông báo**

Manager gõ để duyệt:
```
@approval-notifier APPROVE EXP-XXXXXX
```

---

### Scenario 3 — HIGH Risk 🚨 (CFO leo thang)

```
@budget-checker $6000 SAP software license, Engineering dept, vendor: SAP
```

Pipeline: Budget TIGHT → NON-COMPLIANT (>$5,000 cần CFO, software >$1,000 cần IT) → HIGH → **CFO nhận thông báo**

CFO gõ để từ chối:
```
@approval-notifier REJECT EXP-XXXXXX budget not available this quarter
```

---

### Scenario 4 — Web Dashboard 🖥️

1. Mở `http://YOUR_IP:5000`
2. Điền form: họ tên, số tiền, phòng ban, mô tả, vendor
3. Bấm **Gửi Yêu Cầu**
4. Pipeline tự động chạy, kết quả hiện trong Band và dashboard

---

## 10. Scale lên Enterprise

Hiện tại là **demo hoạt động thật** — pipeline đầy đủ, deploy trên VPS 24/7.

| Hạng Mục | Demo (Hiện Tại) | Production (Enterprise) |
|---|---|---|
| Database | SQLite | PostgreSQL / MySQL HA |
| Authentication | Không có | SSO / OAuth2 (Google, Microsoft) |
| Notification | Band only | Band + Email + Slack |
| Multi-tenant | 1 công ty, 1 room | Nhiều công ty, room riêng mỗi phòng ban |
| Scale | Single VPS | Kubernetes / Cloud Run |
| Monitoring | Docker logs | Grafana + Prometheus |

---

## 11. Cấu trúc Project

```
.
├── main.py              # 4 AI agents + message sender
├── dashboard.py         # Flask web UI (employee form)
├── tools.py             # LangChain tools wrapping SQLite
├── db.py                # Database layer (budgets, expenses, audit)
├── monitor.py           # Budget monitor (zero LLM cost)
├── Dockerfile           # Docker image
├── docker-compose.yml   # 2 services: agents + dashboard
├── start.bat            # One-click launcher (Windows)
├── pyproject.toml       # Python dependencies
└── .env.example         # Environment variable template
```

---

## License

MIT

---

*Built for Band of Agents Hackathon 2026 · Track 1: Internal Enterprise Workflows*  
*Powered by Band SDK + AI/ML API (GPT-4o) + Featherless AI (Llama 3.1 70B)*
