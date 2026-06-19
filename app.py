"""
Combined web app — Employee Dashboard + Admin Panel
Port 5000 | Tab 1: Submit Expense | Tab 2: Admin Panel
"""
import os
import db
import httpx
from flask import Flask, jsonify, render_template_string, request
from dotenv import load_dotenv

load_dotenv()
db.init_db()

app = Flask(__name__)

BAND_BASE = "https://app.band.ai/api/v1/agent"
_room_ids: list[str] = []


def _fetch_rooms_fresh() -> list[str]:
    global _room_ids
    key = os.environ.get("BAND_RISK_EVALUATOR_KEY", "")
    if not key:
        return _room_ids
    try:
        r = httpx.get(f"{BAND_BASE}/chats", headers={"X-API-Key": key}, timeout=10)
        if r.is_success:
            _room_ids = [c["id"] for c in r.json().get("data", [])]
    except Exception as e:
        print(f"[web] room fetch error: {e}")
    return _room_ids


def _band_send(content: str) -> bool:
    _fetch_rooms_fresh()
    key = os.environ.get("BAND_RISK_EVALUATOR_KEY", "")
    notifier_id = os.environ.get("BAND_APPROVAL_NOTIFIER_ID", "")
    rooms = _room_ids
    if not rooms or not key:
        return False
    payload = {
        "message": {
            "content": content,
            "mentions": [{"id": notifier_id, "handle": "approval-notifier", "name": "Approval Notifier"}],
        }
    }
    headers = {"X-API-Key": key, "Content-Type": "application/json"}
    ok = False
    for room_id in rooms:
        try:
            r = httpx.post(f"{BAND_BASE}/chats/{room_id}/messages",
                           json=payload, headers=headers, timeout=10)
            if r.is_success:
                ok = True
        except Exception as e:
            print(f"[web] send error: {e}")
    return ok


HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Expense Approval System — AI Powered</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --primary: #4f46e5; --primary-hover: #4338ca; --primary-light: #e0e7ff;
  --success: #10b981; --success-bg: #d1fae5;
  --warning: #f59e0b; --warning-bg: #fef3c7;
  --danger: #ef4444;  --danger-bg: #fee2e2;
  --text: #0f172a; --muted: #64748b; --border: #e2e8f0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Plus Jakarta Sans', sans-serif;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4f46e5 100%);
  min-height: 100vh; -webkit-font-smoothing: antialiased;
}

/* ── Header ── */
.header {
  padding: 16px 28px;
  display: flex; align-items: center; justify-content: space-between;
}
.logo { display: flex; align-items: center; gap: 12px; }
.logo-icon {
  width: 40px; height: 40px; background: rgba(255,255,255,0.15);
  border-radius: 12px; display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem; backdrop-filter: blur(8px);
}
.logo h1 { font-size: 1rem; font-weight: 800; color: #fff; }
.logo p  { font-size: 0.72rem; color: rgba(255,255,255,0.7); font-weight: 500; }
.live-badge {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.1); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.2);
  padding: 7px 14px; border-radius: 999px; color: #fff; font-size: 0.8rem; font-weight: 600;
}
.dot { width: 8px; height: 8px; background: #4ade80; border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(74,222,128,0.4); } 50%{ box-shadow:0 0 0 6px rgba(74,222,128,0); } }

/* ── Top tabs ── */
.top-tabs {
  display: flex; gap: 4px; padding: 0 28px 0;
  margin-bottom: 0;
}
.top-tab {
  padding: 12px 28px; border: none; border-radius: 12px 12px 0 0;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; font-weight: 700;
  cursor: pointer; transition: all 0.2s;
  color: rgba(255,255,255,0.6); background: rgba(255,255,255,0.08);
  border-bottom: 3px solid transparent;
}
.top-tab.active {
  color: #fff; background: rgba(255,255,255,0.15);
  border-bottom: 3px solid #a5b4fc;
}
.top-tab:hover:not(.active) { color: rgba(255,255,255,0.85); background: rgba(255,255,255,0.12); }

/* ── Content area ── */
.content { padding: 24px 28px 48px; }

/* ── Top panel: Submit ── */
#main-submit { display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-start; }

.form-card {
  background: #fff; border-radius: 20px; padding: 36px;
  width: 100%; max-width: 520px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.form-title { font-size: 1.3rem; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.form-sub   { font-size: 0.83rem; color: var(--muted); font-weight: 500; margin-bottom: 24px; }
.form-grid  { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.fg { display: flex; flex-direction: column; gap: 5px; }
.fg.full { grid-column: 1/-1; }
.fg label { font-size: 0.75rem; font-weight: 700; color: var(--text); text-transform: uppercase; letter-spacing: 0.5px; }
.fg input, .fg select {
  border: 1.5px solid var(--border); border-radius: 10px;
  padding: 10px 13px; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.875rem; font-weight: 500; color: var(--text);
  outline: none; transition: all 0.2s; background: #fff;
}
.fg input::placeholder { color: #94a3b8; }
.fg input:focus, .fg select:focus {
  border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-light);
}
.btn-send {
  width: 100%; margin-top: 20px; padding: 13px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; border: none; border-radius: 12px;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.95rem; font-weight: 700; cursor: pointer;
  box-shadow: 0 4px 16px rgba(79,70,229,0.35); transition: all 0.2s;
}
.btn-send:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(79,70,229,0.4); }
.btn-send:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.info-steps {
  margin-top: 20px; padding: 14px; background: var(--primary-light);
  border-radius: 12px; display: flex; flex-direction: column; gap: 7px;
}
.step { display: flex; align-items: center; gap: 10px; font-size: 0.78rem; font-weight: 600; color: var(--primary-hover); }
.step-num {
  width: 20px; height: 20px; background: var(--primary); color: #fff;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 0.65rem; font-weight: 800; flex-shrink: 0;
}

.requests-card {
  background: #fff; border-radius: 20px; padding: 28px;
  width: 100%; max-width: 520px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.requests-title { font-size: 0.95rem; font-weight: 800; color: var(--text); margin-bottom: 3px; }
.requests-sub   { font-size: 0.78rem; color: var(--muted); margin-bottom: 18px; }
.req-item {
  padding: 12px 0; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.req-item:last-child { border-bottom: none; padding-bottom: 0; }
.req-id   { font-size: 0.7rem; font-weight: 700; color: var(--primary); font-family: monospace; }
.req-desc { font-size: 0.83rem; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.req-meta { font-size: 0.72rem; color: var(--muted); margin-top: 2px; }
.req-amount { font-size: 0.875rem; font-weight: 800; color: var(--text); text-align: right; }
.badge { display: inline-block; padding: 3px 9px; border-radius: 999px; font-size: 0.68rem; font-weight: 700; margin-top: 3px; }
.b-approved { background: var(--success-bg); color: #059669; }
.b-pending  { background: var(--warning-bg); color: #b45309; }
.b-rejected { background: var(--danger-bg);  color: #dc2626; }
.b-cfo      { background: #f3e8ff; color: #7c3aed; }
.b-manager  { background: var(--primary-light); color: var(--primary-hover); }
.empty-sm   { text-align: center; padding: 28px 0; color: var(--muted); font-size: 0.83rem; font-weight: 600; }

/* ── Admin panel ── */
#main-admin { display: none; }

.stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 20px; }
.stat-card {
  background: rgba(255,255,255,0.1); backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px; padding: 18px 20px; color: #fff;
}
.stat-label { font-size: 0.7rem; font-weight: 700; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-val   { font-size: 1.8rem; font-weight: 800; margin-top: 3px; }
.stat-sub   { font-size: 0.7rem; opacity: 0.55; margin-top: 1px; }

.sub-tabs {
  display: flex; gap: 3px;
  background: rgba(255,255,255,0.1); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.15);
  padding: 3px; border-radius: 10px; margin-bottom: 18px; width: fit-content;
}
.sub-tab-btn {
  padding: 8px 18px; border: none; border-radius: 7px;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.83rem; font-weight: 700;
  cursor: pointer; transition: all 0.2s; color: rgba(255,255,255,0.65); background: transparent;
}
.sub-tab-btn.active { background: #fff; color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.12); }

.sub-panel { display: none; }
.sub-panel.active { display: block; }

/* ── Expense cards ── */
.cards { display: flex; flex-direction: column; gap: 12px; }
.exp-card {
  background: #fff; border-radius: 14px; padding: 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08); transition: transform 0.15s;
}
.exp-card:hover { transform: translateY(-1px); }
.exp-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.exp-id     { font-size: 0.7rem; font-weight: 700; color: var(--primary); font-family: monospace; margin-bottom: 3px; }
.exp-desc   { font-size: 0.95rem; font-weight: 700; color: var(--text); }
.exp-meta   { font-size: 0.8rem; color: var(--muted); font-weight: 500; margin-top: 3px; }
.exp-amount { font-size: 1.5rem; font-weight: 800; color: var(--text); text-align: right; }
.exp-card-mid {
  display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px;
  padding-top: 12px; border-top: 1px solid var(--border);
}
.tag { padding: 3px 9px; border-radius: 999px; font-size: 0.7rem; font-weight: 700; }
.tag-high   { background: var(--danger-bg); color: #dc2626; }
.tag-medium { background: var(--warning-bg); color: #b45309; }
.tag-type   { background: var(--primary-light); color: var(--primary-hover); }
.tag-dept   { background: #f1f5f9; color: #475569; }
.tag-status { background: #f3e8ff; color: #7c3aed; }
.exp-actions { display: flex; gap: 10px; margin-top: 14px; }
.btn-approve {
  flex: 1; padding: 11px; border: none; border-radius: 9px;
  background: linear-gradient(135deg, #10b981, #059669); color: #fff;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 700;
  cursor: pointer; box-shadow: 0 3px 12px rgba(16,185,129,0.3); transition: all 0.2s;
}
.btn-approve:hover { transform: translateY(-1px); }
.btn-approve:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.btn-reject {
  flex: 1; padding: 11px; border: none; border-radius: 9px;
  background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 700;
  cursor: pointer; box-shadow: 0 3px 12px rgba(239,68,68,0.3); transition: all 0.2s;
}
.btn-reject:hover { transform: translateY(-1px); }
.btn-reject:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.reject-form {
  display: none; margin-top: 10px; padding: 14px;
  background: #fff5f5; border: 1.5px solid #fca5a5; border-radius: 10px;
}
.reject-form.show { display: block; }
.reject-form label { font-size: 0.75rem; font-weight: 700; color: #dc2626; display: block; margin-bottom: 7px; }
.reject-form input {
  width: 100%; padding: 9px 11px; border: 1.5px solid #fca5a5;
  border-radius: 8px; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.85rem; outline: none; margin-bottom: 9px; color: var(--text); background: #fff;
}
.reject-actions { display: flex; gap: 8px; }
.btn-confirm-reject {
  padding: 9px 18px; background: var(--danger); color: #fff; border: none;
  border-radius: 8px; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.85rem; font-weight: 700; cursor: pointer;
}
.btn-cancel {
  padding: 9px 18px; background: #fff; color: var(--muted);
  border: 1.5px solid var(--border); border-radius: 8px;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.85rem; font-weight: 600; cursor: pointer;
}

/* ── History table ── */
.table-wrap { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
table { width: 100%; border-collapse: collapse; }
thead { background: #f8fafc; }
th { padding: 12px 14px; text-align: left; font-size: 0.7rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
td { padding: 11px 14px; font-size: 0.83rem; font-weight: 500; color: var(--text); border-bottom: 1px solid var(--border); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8fafc; }
.td-id { font-family: monospace; font-size: 0.72rem; font-weight: 700; color: var(--primary); }
.td-amount { font-weight: 800; }
.td-desc { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-date { font-size: 0.72rem; color: var(--muted); white-space: nowrap; }
.b-approved        { background: var(--success-bg); color: #059669; }
.b-pending         { background: var(--warning-bg); color: #b45309; }
.b-rejected        { background: var(--danger-bg);  color: #dc2626; }
.b-pending_manager { background: var(--primary-light); color: var(--primary-hover); }
.b-pending_cfo     { background: #f3e8ff; color: #7c3aed; }
.b-low    { background: var(--success-bg); color: #059669; }
.b-medium { background: var(--warning-bg); color: #b45309; }
.b-high   { background: var(--danger-bg);  color: #dc2626; }

/* ── Live Feed ── */
.feed-wrap { background: #fff; border-radius: 14px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); overflow: hidden; }
.feed-header {
  padding: 14px 18px; background: #f8fafc; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
}
.feed-header h3 { font-size: 0.85rem; font-weight: 700; color: var(--text); }
.feed-header span { font-size: 0.72rem; color: var(--muted); }
.feed-body { padding: 0; max-height: 560px; overflow-y: auto; }
.msg-item { padding: 12px 18px; border-bottom: 1px solid var(--border); display: flex; gap: 10px; align-items: flex-start; }
.msg-item:last-child { border-bottom: none; }
.msg-avatar { width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; }
.av-budget   { background: #dbeafe; color: #1d4ed8; }
.av-policy   { background: #fef3c7; color: #92400e; }
.av-risk     { background: #fee2e2; color: #991b1b; }
.av-approval { background: #d1fae5; color: #065f46; }
.av-system   { background: #f1f5f9; color: #475569; }
.msg-body { flex: 1; min-width: 0; }
.msg-sender { font-size: 0.72rem; font-weight: 700; color: var(--primary); margin-bottom: 3px; }
.msg-content { font-size: 0.8rem; color: var(--text); line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.msg-time { font-size: 0.67rem; color: var(--muted); margin-top: 3px; }
.feed-empty { padding: 40px; text-align: center; color: var(--muted); font-size: 0.83rem; }

/* ── Budget ── */
.budget-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.budget-header h2 { font-size: 0.95rem; font-weight: 800; color: #fff; }
.btn-reset-all {
  padding: 9px 18px; background: rgba(255,255,255,0.15); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.3); color: #fff; border-radius: 9px;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.83rem; font-weight: 700;
  cursor: pointer; transition: all 0.2s;
}
.btn-reset-all:hover { background: rgba(255,255,255,0.25); }
.budget-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); gap: 14px; }
.budget-card { background: #fff; border-radius: 14px; padding: 20px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
.budget-dept { font-size: 0.95rem; font-weight: 800; color: var(--text); margin-bottom: 10px; }
.budget-row  { display: flex; justify-content: space-between; margin-bottom: 5px; }
.budget-lbl  { font-size: 0.75rem; color: var(--muted); font-weight: 600; }
.budget-val  { font-size: 0.83rem; font-weight: 700; color: var(--text); }
.budget-bar-wrap { background: var(--border); border-radius: 999px; height: 7px; margin: 10px 0; overflow: hidden; }
.budget-bar { height: 100%; border-radius: 999px; transition: width 0.4s; }
.bar-ok   { background: linear-gradient(90deg, #10b981, #34d399); }
.bar-warn { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar-over { background: linear-gradient(90deg, #ef4444, #f87171); }
.budget-pct { font-size: 0.72rem; color: var(--muted); margin-bottom: 12px; text-align: right; }
.btn-reset-dept {
  width: 100%; padding: 9px; background: var(--primary-light); color: var(--primary);
  border: none; border-radius: 9px; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.83rem; font-weight: 700; cursor: pointer; transition: all 0.2s;
}
.btn-reset-dept:hover { background: var(--primary); color: #fff; }

/* ── Empty ── */
.empty-box {
  text-align: center; padding: 50px 24px; background: #fff; border-radius: 14px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}
.empty-box .ei { font-size: 2.5rem; margin-bottom: 12px; }
.empty-box h3  { font-size: 0.95rem; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.empty-box p   { font-size: 0.82rem; color: var(--muted); }

/* ── Toast ── */
.toast {
  position: fixed; bottom: 24px; right: 24px; z-index: 9999;
  padding: 13px 18px; border-radius: 12px; background: #fff;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12); font-size: 0.875rem; font-weight: 700;
  color: var(--text); display: none; align-items: center; gap: 10px;
}
.toast.show    { display: flex; }
.toast.success { border-left: 5px solid var(--success); }
.toast.error   { border-left: 5px solid var(--danger); }

@media (max-width: 768px) {
  .stats { grid-template-columns: 1fr 1fr; }
  .content { padding: 16px 14px 48px; }
  .header { padding: 14px 16px; }
  .top-tabs { padding: 0 14px; }
  #main-submit { flex-direction: column; }
}
</style>
</head>
<body>

<header class="header">
  <div class="logo">
    <div class="logo-icon">💼</div>
    <div>
      <h1>Expense Approval System</h1>
      <p>AI-Powered · 4 Agents · GPT-4o + Llama 3.1 70B</p>
    </div>
  </div>
  <div class="live-badge"><span class="dot"></span> AI Agents Online</div>
</header>

<!-- Top-level tabs -->
<div class="top-tabs">
  <button class="top-tab active" id="tab-submit" onclick="switchMain('submit')">📝 Gửi Yêu Cầu</button>
  <button class="top-tab" id="tab-admin" onclick="switchMain('admin')">🛡️ Admin Panel</button>
</div>

<div class="content">

  <!-- ══════════ TAB 1: SUBMIT ══════════ -->
  <div id="main-submit">
    <div class="form-card">
      <div class="form-title">Tạo Yêu Cầu Chi Phí</div>
      <div class="form-sub">Điền thông tin bên dưới. AI sẽ xử lý tự động qua pipeline 4 agent.</div>
      <div class="form-grid">
        <div class="fg">
          <label>Họ Tên</label>
          <input type="text" id="f-name" placeholder="Nguyễn Văn A">
        </div>
        <div class="fg">
          <label>Số Tiền (USD)</label>
          <input type="number" id="f-amount" placeholder="500" min="1">
        </div>
        <div class="fg">
          <label>Phòng Ban</label>
          <select id="f-dept">
            <option value="Engineering">Kỹ Thuật</option>
            <option value="Marketing">Marketing</option>
            <option value="HR">Nhân Sự</option>
            <option value="Operations">Vận Hành</option>
            <option value="Finance">Tài Chính</option>
            <option value="Sales">Kinh Doanh</option>
          </select>
        </div>
        <div class="fg">
          <label>Nhà Cung Cấp</label>
          <input type="text" id="f-vendor" placeholder="Amazon, SAP...">
        </div>
        <div class="fg full">
          <label>Mô Tả Chi Tiết</label>
          <input type="text" id="f-desc" placeholder="VD: Mua bản quyền phần mềm AWS cho team Engineering">
        </div>
      </div>
      <button class="btn-send" id="btn-send" onclick="submitForm()">Gửi Yêu Cầu</button>
      <div class="info-steps">
        <div class="step"><span class="step-num">1</span> Budget Checker (GPT-4o) — kiểm tra ngân sách</div>
        <div class="step"><span class="step-num">2</span> Policy Checker (Llama 3.1 70B) — kiểm tra quy định</div>
        <div class="step"><span class="step-num">3</span> Risk Evaluator → Approval Notifier — quyết định</div>
      </div>
    </div>

    <div class="requests-card">
      <div class="requests-title">Yêu Cầu Gần Đây</div>
      <div class="requests-sub">Tự động cập nhật mỗi 5 giây</div>
      <div id="req-list"><div class="empty-sm">Chưa có yêu cầu nào</div></div>
    </div>
  </div>

  <!-- ══════════ TAB 2: ADMIN ══════════ -->
  <div id="main-admin">

    <!-- Stats -->
    <div class="stats">
      <div class="stat-card">
        <div class="stat-label">Chờ Duyệt</div>
        <div class="stat-val" id="s-pending">—</div>
        <div class="stat-sub">Cần xem xét</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Đã Duyệt</div>
        <div class="stat-val" id="s-approved">—</div>
        <div class="stat-sub">Tháng này</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Từ Chối</div>
        <div class="stat-val" id="s-rejected">—</div>
        <div class="stat-sub">Tháng này</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tổng Đã Chi</div>
        <div class="stat-val" id="s-amount">—</div>
        <div class="stat-sub">Đã được duyệt</div>
      </div>
    </div>

    <!-- Sub-tabs -->
    <div class="sub-tabs">
      <button class="sub-tab-btn active" onclick="switchSub('pending',this)">Chờ Duyệt <span id="pending-count"></span></button>
      <button class="sub-tab-btn" onclick="switchSub('history',this)">Lịch Sử</button>
      <button class="sub-tab-btn" onclick="switchSub('feed',this)">Live Feed <span id="feed-count"></span></button>
      <button class="sub-tab-btn" onclick="switchSub('budget',this)">Ngân Sách</button>
    </div>

    <div class="sub-panel active" id="sub-pending">
      <div class="cards" id="pending-list">
        <div class="empty-box"><div class="ei">✅</div><h3>Không có yêu cầu nào đang chờ</h3><p>Tất cả đã được xử lý</p></div>
      </div>
    </div>

    <div class="sub-panel" id="sub-history">
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Expense ID</th><th>Người YC</th><th>Số Tiền</th>
            <th>Phòng Ban</th><th>Loại</th><th>Mô Tả</th>
            <th>Rủi Ro</th><th>Trạng Thái</th><th>Ngày Tạo</th>
          </tr></thead>
          <tbody id="history-body">
            <tr><td colspan="9" style="text-align:center;padding:36px;color:#94a3b8">Đang tải...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="sub-panel" id="sub-feed">
      <div class="feed-wrap">
        <div class="feed-header">
          <h3>Agent Activity — Live Feed</h3>
          <span id="feed-ts">Đang tải...</span>
        </div>
        <div class="feed-body" id="feed-body">
          <div class="feed-empty">Chưa có hoạt động nào</div>
        </div>
      </div>
    </div>

    <div class="sub-panel" id="sub-budget">
      <div class="budget-header">
        <h2>Ngân Sách Phòng Ban</h2>
        <button class="btn-reset-all" onclick="resetAll()">↺ Reset Tất Cả</button>
      </div>
      <div class="budget-grid" id="budget-grid">
        <div style="color:#fff;opacity:0.7;padding:20px">Đang tải...</div>
      </div>
    </div>

  </div><!-- /main-admin -->

</div><!-- /content -->

<div class="toast" id="toast"></div>

<script>
/* ── Tab switching ── */
function switchMain(tab) {
  ['submit','admin'].forEach(t => {
    document.getElementById('main-' + t).style.display = t === tab ? (t==='submit'?'flex':'block') : 'none';
    document.getElementById('tab-' + t).classList.toggle('active', t === tab);
  });
  if (tab === 'admin') { loadPending(); loadHistory(); loadFeed(); loadBudget(); }
}

function switchSub(tab, btn) {
  document.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('sub-' + tab).classList.add('active');
}

/* ── Toast ── */
function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.innerHTML = (type==='success'?'✅':'❌') + ' ' + msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 4000);
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('vi-VN') + ' ' + d.toLocaleTimeString('vi-VN', {hour:'2-digit',minute:'2-digit'});
}

const statusMap = {
  APPROVED:        ['b-approved','Đã Duyệt'],
  REJECTED:        ['b-rejected','Từ Chối'],
  PENDING:         ['b-pending','Đang Xử Lý'],
  PENDING_MANAGER: ['b-pending_manager','Chờ Manager'],
  PENDING_CFO:     ['b-pending_cfo','Chờ CFO'],
};

/* ── Submit form ── */
async function submitForm() {
  const name   = document.getElementById('f-name').value.trim();
  const amount = document.getElementById('f-amount').value.trim();
  const dept   = document.getElementById('f-dept').value;
  const vendor = document.getElementById('f-vendor').value.trim() || 'N/A';
  const desc   = document.getElementById('f-desc').value.trim();
  if (!name || !amount || !desc) {
    showToast('Vui lòng nhập đầy đủ: Họ tên, Số tiền, Mô tả.', 'error'); return;
  }
  const btn = document.getElementById('btn-send');
  btn.disabled = true; btn.textContent = 'Đang gửi...';
  try {
    const res = await fetch('/api/submit', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({requester:name, amount, department:dept, vendor, description:desc})
    });
    const d = await res.json();
    if (res.ok) {
      showToast('Gửi thành công! AI đang xử lý...', 'success');
      document.getElementById('f-name').value = '';
      document.getElementById('f-amount').value = '';
      document.getElementById('f-desc').value = '';
      document.getElementById('f-vendor').value = '';
      loadRequests();
    } else { showToast(d.error || 'Gửi thất bại', 'error'); }
  } catch { showToast('Lỗi kết nối', 'error'); }
  finally { btn.disabled = false; btn.textContent = 'Gửi Yêu Cầu'; }
}

async function loadRequests() {
  try {
    const r = await fetch('/api/data');
    const d = await r.json();
    const list = document.getElementById('req-list');
    if (!d.expenses || d.expenses.length === 0) {
      list.innerHTML = '<div class="empty-sm">Chưa có yêu cầu nào</div>'; return;
    }
    list.innerHTML = d.expenses.map(e => {
      const [cls, label] = statusMap[e.status] || ['b-pending', e.status];
      return `<div class="req-item">
        <div style="flex:1;min-width:0">
          <div class="req-id">${e.id}</div>
          <div class="req-desc">${e.department} · ${e.requester||'—'}</div>
          <div class="req-meta">${(e.description||'').slice(0,40)||e.expense_type||''}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div class="req-amount">$${(e.amount||0).toLocaleString()}</div>
          <div class="badge ${cls}">${label}</div>
        </div>
      </div>`;
    }).join('');
  } catch {}
}

/* ── Pending ── */
let showAllPending = false;

function removeCard(id) {
  const c = document.getElementById('card-' + id);
  if (c) { c.style.transition='opacity 0.3s,transform 0.3s'; c.style.opacity='0'; c.style.transform='translateX(30px)'; setTimeout(()=>c.remove(),320); }
}

async function approve(id, btn) {
  btn.disabled=true; btn.textContent='Đang gửi...';
  try {
    const r = await fetch('/api/approve/'+id, {method:'POST'});
    const d = await r.json();
    if (r.ok) { showToast('Đã duyệt '+id+'!'); removeCard(id); }
    else { showToast(d.error||'Lỗi','error'); btn.disabled=false; btn.textContent='✅ Duyệt'; }
  } catch { showToast('Lỗi kết nối','error'); btn.disabled=false; btn.textContent='✅ Duyệt'; }
}

function toggleRejectForm(id) { document.getElementById('reject-form-'+id).classList.toggle('show'); }

async function confirmReject(id) {
  const reason = (document.getElementById('reject-reason-'+id).value||'').trim()||'Rejected by admin';
  const btn = document.getElementById('reject-confirm-btn-'+id);
  btn.disabled=true; btn.textContent='Đang gửi...';
  try {
    const r = await fetch('/api/reject/'+id, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({reason}),
    });
    const d = await r.json();
    if (r.ok) { showToast('Đã từ chối '+id+'!'); removeCard(id); }
    else { showToast(d.error||'Lỗi','error'); btn.disabled=false; btn.textContent='Xác Nhận'; }
  } catch { showToast('Lỗi kết nối','error'); btn.disabled=false; btn.textContent='Xác Nhận'; }
}

async function dismiss(id) {
  await fetch('/api/dismiss/'+id, {method:'POST'});
  removeCard(id); showToast('Đã bỏ qua '+id);
}

async function loadPending() {
  try {
    const r = await fetch('/api/pending'+(showAllPending?'?all=1':''));
    const d = await r.json();
    const list = document.getElementById('pending-list');
    const cnt  = document.getElementById('pending-count');
    if (!d.expenses||d.expenses.length===0) {
      cnt.textContent='';
      list.innerHTML=`<div class="empty-box"><div class="ei">✅</div><h3>Không có yêu cầu nào đang chờ</h3><p>${showAllPending?'Tất cả đã xử lý':'24h gần nhất — <a href="#" onclick="toggleShowAll();return false" style="color:var(--primary)">Xem tất cả</a>'}</p></div>`;
      return;
    }
    cnt.textContent='('+d.expenses.length+')';
    const toggle=`<div style="margin-bottom:10px;text-align:right"><button onclick="toggleShowAll()" style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#fff;padding:5px 12px;border-radius:7px;font-size:0.75rem;font-weight:700;cursor:pointer;font-family:inherit">${showAllPending?'⏱ Chỉ 24h':'📋 Xem tất cả'}</button></div>`;
    const cards=d.expenses.map(e=>{
      const rc=e.risk_level==='HIGH'?'tag-high':e.risk_level==='MEDIUM'?'tag-medium':'';
      const rl=e.risk_level==='HIGH'?'🔴 HIGH':e.risk_level==='MEDIUM'?'🟡 MEDIUM':e.risk_level==='LOW'?'🟢 LOW':'⏳ Processing';
      const sl=e.status==='PENDING_CFO'?'Chờ CFO':e.status==='PENDING_MANAGER'?'Chờ Manager':'Đang xử lý';
      return `<div class="exp-card" id="card-${e.id}">
        <div class="exp-card-top">
          <div style="flex:1;min-width:0">
            <div class="exp-id">${e.id}</div>
            <div class="exp-desc">${e.description||e.expense_type||'N/A'}</div>
            <div class="exp-meta">${e.requester||'—'} · ${e.department} · ${fmtDate(e.created_at)}</div>
          </div>
          <div style="display:flex;align-items:flex-start;gap:8px">
            <div class="exp-amount">$${(e.amount||0).toLocaleString()}</div>
            <button onclick="dismiss('${e.id}')" title="Bỏ qua" style="background:#f1f5f9;border:none;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:0.75rem;color:#94a3b8;font-weight:700">✕</button>
          </div>
        </div>
        <div class="exp-card-mid">
          <span class="tag ${rc||'tag-dept'}">${rl}</span>
          <span class="tag tag-type">${e.expense_type||'other'}</span>
          <span class="tag tag-dept">${e.department}</span>
          ${e.vendor&&e.vendor!=='N/A'?`<span class="tag tag-dept">${e.vendor}</span>`:''}
          <span class="tag tag-status">${sl}</span>
        </div>
        <div class="exp-actions">
          <button class="btn-approve" onclick="approve('${e.id}',this)">✅ Duyệt</button>
          <button class="btn-reject"  onclick="toggleRejectForm('${e.id}')">❌ Từ Chối</button>
        </div>
        <div class="reject-form" id="reject-form-${e.id}">
          <label>Lý do từ chối</label>
          <input type="text" id="reject-reason-${e.id}" placeholder="VD: Ngân sách không đủ...">
          <div class="reject-actions">
            <button class="btn-confirm-reject" id="reject-confirm-btn-${e.id}" onclick="confirmReject('${e.id}')">Xác Nhận Từ Chối</button>
            <button class="btn-cancel" onclick="toggleRejectForm('${e.id}')">Huỷ</button>
          </div>
        </div>
      </div>`;
    }).join('');
    list.innerHTML=toggle+cards;
  } catch {}
}

function toggleShowAll() { showAllPending=!showAllPending; loadPending(); }

/* ── History ── */
async function loadHistory() {
  try {
    const r = await fetch('/api/history');
    const d = await r.json();
    if (d.stats) {
      document.getElementById('s-pending').textContent  = d.stats.pending  || 0;
      document.getElementById('s-approved').textContent = d.stats.approved || 0;
      document.getElementById('s-rejected').textContent = d.stats.rejected || 0;
      document.getElementById('s-amount').textContent = '$'+(d.stats.total_approved_amount||0).toLocaleString();
    }
    const tbody = document.getElementById('history-body');
    if (!d.expenses||d.expenses.length===0) {
      tbody.innerHTML='<tr><td colspan="9" style="text-align:center;padding:36px;color:#94a3b8">Chưa có giao dịch</td></tr>'; return;
    }
    tbody.innerHTML=d.expenses.map(e=>{
      const [sc,sl]=statusMap[e.status]||['b-pending',e.status];
      const rc=e.risk_level==='HIGH'?'b-high':e.risk_level==='MEDIUM'?'b-medium':e.risk_level==='LOW'?'b-low':'';
      return `<tr>
        <td class="td-id">${e.id}</td>
        <td>${e.requester||'—'}</td>
        <td class="td-amount">$${(e.amount||0).toLocaleString()}</td>
        <td>${e.department}</td>
        <td>${e.expense_type||'—'}</td>
        <td class="td-desc" title="${e.description||''}">${(e.description||'').slice(0,40)||'—'}</td>
        <td>${rc?`<span class="badge ${rc}">${e.risk_level}</span>`:'—'}</td>
        <td><span class="badge ${sc}">${sl}</span></td>
        <td class="td-date">${fmtDate(e.created_at)}</td>
      </tr>`;
    }).join('');
  } catch {}
}

/* ── Live Feed ── */
const agentMeta = {
  'budget-checker':    {label:'Budget Checker',    cls:'av-budget',   icon:'💰'},
  'policychecker':     {label:'Policy Checker',    cls:'av-policy',   icon:'📋'},
  'policy-checker':    {label:'Policy Checker',    cls:'av-policy',   icon:'📋'},
  'risk-evaluator':    {label:'Risk Evaluator',    cls:'av-risk',     icon:'⚠️'},
  'approval-notifier': {label:'Approval Notifier', cls:'av-approval', icon:'✅'},
};
function agentInfo(k) {
  const key=(k||'').toLowerCase();
  for (const [n,v] of Object.entries(agentMeta)) { if(key.includes(n)) return v; }
  return {label:k||'System',cls:'av-system',icon:'⚙️'};
}
function actionColor(a) {
  if(!a) return '#64748b'; const u=a.toUpperCase();
  if(u.includes('APPROVED')||u.includes('APPROVE')) return '#059669';
  if(u.includes('REJECTED')||u.includes('REJECT'))  return '#dc2626';
  if(u.includes('HIGH'))   return '#dc2626';
  if(u.includes('MEDIUM')) return '#b45309';
  if(u.includes('LOW'))    return '#059669';
  if(u.includes('CREATED')) return '#4f46e5';
  return '#475569';
}

async function loadFeed() {
  try {
    const r = await fetch('/api/band-messages');
    const d = await r.json();
    const body=document.getElementById('feed-body');
    const cnt =document.getElementById('feed-count');
    document.getElementById('feed-ts').textContent='Cập nhật: '+new Date().toLocaleTimeString('vi-VN');
    if(!d.messages||d.messages.length===0) {
      cnt.textContent='';
      body.innerHTML='<div class="feed-empty">Chưa có hoạt động. Gửi thử expense request!</div>'; return;
    }
    cnt.textContent='('+d.messages.length+')';
    const atBottom=body.scrollHeight-body.scrollTop<=body.clientHeight+50;
    body.innerHTML=d.messages.map(m=>{
      const info=agentInfo(m.agent);
      const ac=actionColor(m.action);
      const extra=m.amount?` · ${m.expense_id} · $${Number(m.amount).toLocaleString()} · ${m.department}`:(m.expense_id?` · ${m.expense_id}`:'');
      return `<div class="msg-item">
        <div class="msg-avatar ${info.cls}">${info.icon}</div>
        <div class="msg-body">
          <div class="msg-sender">${info.label}<span style="font-weight:500;color:#94a3b8;margin-left:8px;font-size:0.68rem">${extra}</span></div>
          <div class="msg-content">
            <span style="background:#f1f5f9;padding:2px 7px;border-radius:5px;font-size:0.7rem;font-weight:700;color:${ac}">${m.action}</span>
            ${m.details?`<span style="margin-left:8px;color:#475569;font-size:0.78rem">${m.details.replace(/</g,'&lt;')}</span>`:''}
          </div>
          <div class="msg-time">${fmtDate(m.timestamp)}</div>
        </div>
      </div>`;
    }).join('');
    if(atBottom) body.scrollTop=body.scrollHeight;
  } catch {}
}

/* ── Budget ── */
async function loadBudget() {
  try {
    const r=await fetch('/api/budgets');
    const d=await r.json();
    document.getElementById('budget-grid').innerHTML=d.budgets.map(b=>{
      const used=b.monthly_limit-b.remaining;
      const pct=Math.max(0,Math.min(100,(used/b.monthly_limit)*100));
      const bc=pct>=90?'bar-over':pct>=70?'bar-warn':'bar-ok';
      return `<div class="budget-card">
        <div class="budget-dept">${b.department}</div>
        <div class="budget-row"><span class="budget-lbl">Hạn mức</span><span class="budget-val">$${b.monthly_limit.toLocaleString()}</span></div>
        <div class="budget-row"><span class="budget-lbl">Đã dùng</span><span class="budget-val" style="color:${pct>=90?'#dc2626':pct>=70?'#b45309':'#059669'}">$${used.toLocaleString()}</span></div>
        <div class="budget-row"><span class="budget-lbl">Còn lại</span><span class="budget-val">$${b.remaining.toLocaleString()}</span></div>
        <div class="budget-bar-wrap"><div class="budget-bar ${bc}" style="width:${pct}%"></div></div>
        <div class="budget-pct">${pct.toFixed(1)}% đã dùng</div>
        <button class="btn-reset-dept" onclick="resetDept('${b.department}',this)">↺ Reset ngân sách</button>
      </div>`;
    }).join('');
  } catch {}
}

async function resetDept(dept, btn) {
  btn.textContent='Đang reset...'; btn.disabled=true;
  try {
    const r=await fetch('/api/reset-budget/'+encodeURIComponent(dept),{method:'POST'});
    if(r.ok){showToast('Đã reset ngân sách '+dept);loadBudget();}
    else showToast('Lỗi reset','error');
  } catch {showToast('Lỗi kết nối','error');}
  finally{btn.disabled=false;btn.textContent='↺ Reset ngân sách';}
}

async function resetAll() {
  if(!confirm('Reset ngân sách TẤT CẢ phòng ban?')) return;
  try {
    const r=await fetch('/api/reset-all-budgets',{method:'POST'});
    if(r.ok){showToast('Đã reset tất cả');loadBudget();}
    else showToast('Lỗi','error');
  } catch {showToast('Lỗi kết nối','error');}
}

/* ── Auto refresh ── */
loadRequests();
setInterval(loadRequests, 5000);
setInterval(()=>{ loadPending(); loadHistory(); loadFeed(); loadBudget(); }, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


# ── Submit (from dashboard) ──────────────────────────────────────────────────

@app.route("/api/submit", methods=["POST"])
def api_submit():
    data = request.get_json() or {}
    requester   = (data.get("requester") or "").strip()
    amount      = str(data.get("amount") or "").strip()
    department  = (data.get("department") or "Engineering").strip()
    description = (data.get("description") or "").strip()
    vendor      = (data.get("vendor") or "N/A").strip()
    if not requester or not amount or not description:
        return jsonify(error="Name, Amount, and Description are required"), 400
    msg = f"Expense request from {requester}: ${amount} {description}, {department} dept, vendor: {vendor}"
    row_id = db.queue_message(msg)
    return jsonify(ok=True, queued_id=row_id)


@app.route("/api/data")
def api_data():
    with db._conn() as conn:
        expenses = [dict(r) for r in conn.execute(
            "SELECT id, requester, amount, department, expense_type, description, risk_level, status "
            "FROM expenses ORDER BY created_at DESC LIMIT 20"
        ).fetchall()]
    return jsonify(expenses=expenses)


# ── Admin endpoints (from admin.py) ──────────────────────────────────────────

@app.route("/api/pending")
def api_pending():
    show_all = request.args.get("all") == "1"
    with db._conn() as conn:
        q = """SELECT id, requester, amount, department, expense_type,
                      description, vendor, status, risk_level, created_at
               FROM expenses WHERE status NOT IN ('APPROVED','REJECTED','DISMISSED')"""
        if not show_all:
            q += " AND created_at >= datetime('now', '-24 hours')"
        q += " ORDER BY created_at DESC"
        rows = conn.execute(q).fetchall()
    return jsonify(expenses=[dict(r) for r in rows], show_all=show_all)


@app.route("/api/history")
def api_history():
    with db._conn() as conn:
        rows = conn.execute(
            "SELECT id, requester, amount, department, expense_type, description, "
            "vendor, status, risk_level, created_at FROM expenses ORDER BY created_at DESC LIMIT 60"
        ).fetchall()
        stats = dict(conn.execute("""
            SELECT COUNT(*) as total,
              SUM(CASE WHEN status='APPROVED' THEN 1 ELSE 0 END) as approved,
              SUM(CASE WHEN status='REJECTED' THEN 1 ELSE 0 END) as rejected,
              SUM(CASE WHEN status NOT IN ('APPROVED','REJECTED') THEN 1 ELSE 0 END) as pending,
              COALESCE(SUM(CASE WHEN status='APPROVED' THEN amount ELSE 0 END),0) as total_approved_amount
            FROM expenses
        """).fetchone())
    return jsonify(expenses=[dict(r) for r in rows], stats=stats)


@app.route("/api/band-messages")
def api_band_messages():
    with db._conn() as conn:
        rows = conn.execute("""
            SELECT a.expense_id, a.agent, a.action, a.details, a.timestamp,
                   e.requester, e.amount, e.department
            FROM audit_log a LEFT JOIN expenses e ON a.expense_id = e.id
            ORDER BY a.id DESC LIMIT 80
        """).fetchall()
    return jsonify(messages=list(reversed([dict(r) for r in rows])))


@app.route("/api/budgets")
def api_budgets():
    return jsonify(budgets=db.get_all_budgets())


@app.route("/api/reset-budget/<dept>", methods=["POST"])
def api_reset_budget(dept):
    db.reset_budget(dept)
    return jsonify(ok=True)


@app.route("/api/reset-all-budgets", methods=["POST"])
def api_reset_all():
    db.reset_all_budgets()
    return jsonify(ok=True)


@app.route("/api/approve/<expense_id>", methods=["POST"])
def api_approve(expense_id):
    success = db.approve_expense(expense_id, approved_by="manager-web")
    if not success:
        return jsonify(ok=False, error="Expense not found"), 404
    row = db.get_expense(expense_id)
    requester  = row["requester"] if row else "—"
    amount_str = f"${row['amount']:,.0f} ({row['department']})" if row else "—"
    notify = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  EXPENSE DECISION — {expense_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Status:     ✅ APPROVED\n"
        f"  Requester:  {requester}\n"
        f"  Amount:     {amount_str}\n"
        f"  Decided by: Manager (Admin Panel)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Audit trail saved ✓ | Budget updated ✓"
    )
    _band_send(notify)
    return jsonify(ok=True)


@app.route("/api/reject/<expense_id>", methods=["POST"])
def api_reject(expense_id):
    data = request.get_json() or {}
    reason = (data.get("reason") or "Rejected by admin").strip()
    success = db.reject_expense(expense_id, reason=reason, rejected_by="manager-web")
    if not success:
        return jsonify(ok=False, error="Expense not found"), 404
    row = db.get_expense(expense_id)
    requester  = row["requester"] if row else "—"
    amount_str = f"${row['amount']:,.0f} ({row['department']})" if row else "—"
    notify = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  EXPENSE DECISION — {expense_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Status:     ❌ REJECTED\n"
        f"  Requester:  {requester}\n"
        f"  Amount:     {amount_str}\n"
        f"  Reason:     {reason}\n"
        f"  Decided by: Manager (Admin Panel)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Audit trail saved ✓"
    )
    _band_send(notify)
    return jsonify(ok=True)


@app.route("/api/dismiss/<expense_id>", methods=["POST"])
def api_dismiss(expense_id):
    db.update_expense(expense_id, status="DISMISSED")
    db.log_audit(expense_id, "admin-panel", "DISMISSED", "Manually dismissed")
    return jsonify(ok=True)


if __name__ == "__main__":
    print("Expense Approval System → http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
