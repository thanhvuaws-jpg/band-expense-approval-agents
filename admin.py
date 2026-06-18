"""
Admin Panel — Expense Approval System
Managers can review/approve/reject expenses, watch live Band feed, and manage budgets.
Port 5001
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


def _get_rooms() -> list[str]:
    global _room_ids
    if _room_ids:
        return _room_ids
    key = os.environ.get("BAND_BUDGET_CHECKER_KEY", "")
    if not key:
        return []
    try:
        r = httpx.get(f"{BAND_BASE}/chats", headers={"X-API-Key": key}, timeout=10)
        if r.is_success:
            _room_ids = [c["id"] for c in r.json().get("data", [])]
    except Exception as e:
        print(f"[admin] room fetch error: {e}")
    return _room_ids


def _band_send(content: str) -> bool:
    key = os.environ.get("BAND_BUDGET_CHECKER_KEY", "")
    notifier_id = os.environ.get("BAND_APPROVAL_NOTIFIER_ID", "")
    rooms = _get_rooms()
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
        except Exception:
            pass
    return ok


HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Panel — Expense Approval</title>
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
  padding: 20px 32px;
  display: flex; align-items: center; justify-content: space-between;
}
.logo { display: flex; align-items: center; gap: 12px; }
.logo-icon {
  width: 42px; height: 42px; background: rgba(255,255,255,0.15);
  border-radius: 12px; display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; backdrop-filter: blur(8px);
}
.logo h1 { font-size: 1.1rem; font-weight: 800; color: #fff; }
.logo p  { font-size: 0.75rem; color: rgba(255,255,255,0.7); font-weight: 500; }
.header-right { display: flex; align-items: center; gap: 10px; }
.admin-badge {
  background: rgba(255,255,255,0.15); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.25);
  padding: 8px 16px; border-radius: 999px; color: #fff; font-size: 0.8rem; font-weight: 700;
}
.live-badge {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.1); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.2);
  padding: 8px 16px; border-radius: 999px; color: #fff; font-size: 0.8rem; font-weight: 600;
}
.dot { width: 8px; height: 8px; background: #4ade80; border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(74,222,128,0.4); } 50%{ box-shadow:0 0 0 6px rgba(74,222,128,0); } }

/* ── Layout ── */
.content { padding: 0 24px 48px; max-width: 1100px; margin: 0 auto; }

/* ── Stats ── */
.stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
  background: rgba(255,255,255,0.1); backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 16px; padding: 20px 24px; color: #fff;
}
.stat-label { font-size: 0.72rem; font-weight: 700; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-val   { font-size: 2rem; font-weight: 800; margin-top: 4px; }
.stat-sub   { font-size: 0.72rem; opacity: 0.55; margin-top: 2px; }

/* ── Tabs ── */
.tabs {
  display: flex; gap: 4px;
  background: rgba(255,255,255,0.1); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.15);
  padding: 4px; border-radius: 12px; margin-bottom: 20px; width: fit-content;
}
.tab-btn {
  padding: 10px 22px; border: none; border-radius: 8px;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 700;
  cursor: pointer; transition: all 0.2s; color: rgba(255,255,255,0.7); background: transparent;
}
.tab-btn.active { background: #fff; color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
.panel { display: none; }
.panel.active { display: block; }

/* ── Expense cards ── */
.cards { display: flex; flex-direction: column; gap: 12px; }
.exp-card {
  background: #fff; border-radius: 16px; padding: 24px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08); transition: transform 0.15s;
}
.exp-card:hover { transform: translateY(-1px); }
.exp-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.exp-id     { font-size: 0.72rem; font-weight: 700; color: var(--primary); font-family: monospace; margin-bottom: 4px; }
.exp-desc   { font-size: 1rem; font-weight: 700; color: var(--text); }
.exp-meta   { font-size: 0.82rem; color: var(--muted); font-weight: 500; margin-top: 4px; }
.exp-amount { font-size: 1.6rem; font-weight: 800; color: var(--text); text-align: right; }
.exp-card-mid {
  display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px;
  padding-top: 14px; border-top: 1px solid var(--border);
}
.tag { padding: 4px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 700; }
.tag-high   { background: var(--danger-bg); color: #dc2626; }
.tag-medium { background: var(--warning-bg); color: #b45309; }
.tag-type   { background: var(--primary-light); color: var(--primary-hover); }
.tag-dept   { background: #f1f5f9; color: #475569; }
.tag-status { background: #f3e8ff; color: #7c3aed; }
.exp-actions { display: flex; gap: 10px; margin-top: 16px; }
.btn-approve {
  flex: 1; padding: 12px; border: none; border-radius: 10px;
  background: linear-gradient(135deg, #10b981, #059669); color: #fff;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; font-weight: 700;
  cursor: pointer; box-shadow: 0 3px 12px rgba(16,185,129,0.3); transition: all 0.2s;
}
.btn-approve:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(16,185,129,0.4); }
.btn-approve:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.btn-reject {
  flex: 1; padding: 12px; border: none; border-radius: 10px;
  background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; font-weight: 700;
  cursor: pointer; box-shadow: 0 3px 12px rgba(239,68,68,0.3); transition: all 0.2s;
}
.btn-reject:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(239,68,68,0.4); }
.btn-reject:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.reject-form {
  display: none; margin-top: 12px; padding: 16px;
  background: #fff5f5; border: 1.5px solid #fca5a5; border-radius: 12px;
}
.reject-form.show { display: block; }
.reject-form label { font-size: 0.78rem; font-weight: 700; color: #dc2626; display: block; margin-bottom: 8px; }
.reject-form input {
  width: 100%; padding: 10px 12px; border: 1.5px solid #fca5a5;
  border-radius: 8px; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.875rem; outline: none; margin-bottom: 10px; color: var(--text); background: #fff;
}
.reject-form input:focus { border-color: var(--danger); box-shadow: 0 0 0 3px rgba(239,68,68,0.1); }
.reject-actions { display: flex; gap: 8px; }
.btn-confirm-reject {
  padding: 10px 20px; background: var(--danger); color: #fff; border: none;
  border-radius: 8px; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 700; cursor: pointer;
}
.btn-cancel {
  padding: 10px 20px; background: #fff; color: var(--muted);
  border: 1.5px solid var(--border); border-radius: 8px;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}

/* ── History table ── */
.table-wrap { background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
table { width: 100%; border-collapse: collapse; }
thead { background: #f8fafc; }
th {
  padding: 14px 16px; text-align: left; font-size: 0.72rem; font-weight: 700;
  color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border);
}
td { padding: 13px 16px; font-size: 0.85rem; font-weight: 500; color: var(--text); border-bottom: 1px solid var(--border); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8fafc; }
.td-id     { font-family: monospace; font-size: 0.75rem; font-weight: 700; color: var(--primary); }
.td-amount { font-weight: 800; }
.td-desc   { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-date   { font-size: 0.75rem; color: var(--muted); white-space: nowrap; }

.badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 700; }
.b-approved        { background: var(--success-bg); color: #059669; }
.b-pending         { background: var(--warning-bg); color: #b45309; }
.b-rejected        { background: var(--danger-bg);  color: #dc2626; }
.b-pending_manager { background: var(--primary-light); color: var(--primary-hover); }
.b-pending_cfo     { background: #f3e8ff; color: #7c3aed; }
.b-low    { background: var(--success-bg); color: #059669; }
.b-medium { background: var(--warning-bg); color: #b45309; }
.b-high   { background: var(--danger-bg);  color: #dc2626; }

/* ── Live Feed ── */
.feed-wrap {
  background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  overflow: hidden;
}
.feed-header {
  padding: 16px 20px; background: #f8fafc; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
}
.feed-header h3 { font-size: 0.875rem; font-weight: 700; color: var(--text); }
.feed-header span { font-size: 0.75rem; color: var(--muted); }
.feed-body { padding: 0; max-height: 600px; overflow-y: auto; }
.msg-item {
  padding: 14px 20px; border-bottom: 1px solid var(--border);
  display: flex; gap: 12px; align-items: flex-start;
}
.msg-item:last-child { border-bottom: none; }
.msg-avatar {
  width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 800;
}
.av-budget   { background: #dbeafe; color: #1d4ed8; }
.av-policy   { background: #fef3c7; color: #92400e; }
.av-risk     { background: #fee2e2; color: #991b1b; }
.av-approval { background: #d1fae5; color: #065f46; }
.av-user     { background: #f3e8ff; color: #6b21a8; }
.av-system   { background: #f1f5f9; color: #475569; }
.msg-body { flex: 1; min-width: 0; }
.msg-sender { font-size: 0.75rem; font-weight: 700; color: var(--primary); margin-bottom: 4px; }
.msg-content {
  font-size: 0.82rem; color: var(--text); line-height: 1.5;
  white-space: pre-wrap; word-break: break-word;
}
.msg-time { font-size: 0.7rem; color: var(--muted); margin-top: 4px; }
.feed-empty { padding: 48px; text-align: center; color: var(--muted); font-size: 0.875rem; }

/* ── Budget tab ── */
.budget-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;
}
.budget-header h2 { font-size: 1rem; font-weight: 800; color: #fff; }
.btn-reset-all {
  padding: 10px 20px; background: rgba(255,255,255,0.15); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.3); color: #fff; border-radius: 10px;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 700;
  cursor: pointer; transition: all 0.2s;
}
.btn-reset-all:hover { background: rgba(255,255,255,0.25); }
.budget-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.budget-card {
  background: #fff; border-radius: 16px; padding: 22px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}
.budget-dept { font-size: 1rem; font-weight: 800; color: var(--text); margin-bottom: 12px; }
.budget-row  { display: flex; justify-content: space-between; margin-bottom: 6px; }
.budget-lbl  { font-size: 0.78rem; color: var(--muted); font-weight: 600; }
.budget-val  { font-size: 0.875rem; font-weight: 700; color: var(--text); }
.budget-bar-wrap { background: var(--border); border-radius: 999px; height: 8px; margin: 12px 0; overflow: hidden; }
.budget-bar { height: 100%; border-radius: 999px; transition: width 0.4s ease; }
.bar-ok   { background: linear-gradient(90deg, #10b981, #34d399); }
.bar-warn { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar-over { background: linear-gradient(90deg, #ef4444, #f87171); }
.budget-pct { font-size: 0.75rem; color: var(--muted); margin-bottom: 14px; text-align: right; }
.btn-reset-dept {
  width: 100%; padding: 10px; background: var(--primary-light); color: var(--primary);
  border: none; border-radius: 10px; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.875rem; font-weight: 700; cursor: pointer; transition: all 0.2s;
}
.btn-reset-dept:hover { background: var(--primary); color: #fff; }

/* ── Empty state ── */
.empty {
  text-align: center; padding: 60px 24px; background: #fff; border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}
.empty-icon { font-size: 3rem; margin-bottom: 16px; }
.empty h3   { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 8px; }
.empty p    { font-size: 0.85rem; color: var(--muted); }

/* ── Toast ── */
.toast {
  position: fixed; bottom: 28px; right: 28px; z-index: 999;
  padding: 14px 20px; border-radius: 12px; background: #fff;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12); font-size: 0.9rem; font-weight: 700;
  color: var(--text); display: none; align-items: center; gap: 10px;
}
.toast.show    { display: flex; }
.toast.success { border-left: 5px solid var(--success); }
.toast.error   { border-left: 5px solid var(--danger); }

@media (max-width: 768px) {
  .stats { grid-template-columns: 1fr 1fr; }
  .content { padding: 0 12px 48px; }
  .header { padding: 16px; }
}
</style>
</head>
<body>

<header class="header">
  <div class="logo">
    <div class="logo-icon">🛡️</div>
    <div>
      <h1>Admin Panel</h1>
      <p>Expense Approval System</p>
    </div>
  </div>
  <div class="header-right">
    <div class="admin-badge">Manager Access</div>
    <div class="live-badge"><span class="dot"></span> Auto-sync 5s</div>
  </div>
</header>

<div class="content">

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

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('pending', this)">
      Chờ Duyệt <span id="pending-count"></span>
    </button>
    <button class="tab-btn" onclick="switchTab('history', this)">Lịch Sử</button>
    <button class="tab-btn" onclick="switchTab('feed', this)">
      Live Feed <span id="feed-count"></span>
    </button>
    <button class="tab-btn" onclick="switchTab('budget', this)">Ngân Sách</button>
  </div>

  <!-- Panel: Pending -->
  <div class="panel active" id="panel-pending">
    <div class="cards" id="pending-list">
      <div class="empty">
        <div class="empty-icon">✅</div>
        <h3>Không có yêu cầu nào đang chờ</h3>
        <p>Tất cả đã được xử lý</p>
      </div>
    </div>
  </div>

  <!-- Panel: History -->
  <div class="panel" id="panel-history">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Expense ID</th><th>Người YC</th><th>Số Tiền</th>
            <th>Phòng Ban</th><th>Loại</th><th>Mô Tả</th>
            <th>Rủi Ro</th><th>Trạng Thái</th><th>Ngày Tạo</th>
          </tr>
        </thead>
        <tbody id="history-body">
          <tr><td colspan="9" style="text-align:center;padding:40px;color:#94a3b8">Đang tải...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Panel: Live Feed -->
  <div class="panel" id="panel-feed">
    <div class="feed-wrap">
      <div class="feed-header">
        <h3>Tin nhắn từ Band room</h3>
        <span id="feed-ts">Đang tải...</span>
      </div>
      <div class="feed-body" id="feed-body">
        <div class="feed-empty">Đang kết nối Band...</div>
      </div>
    </div>
  </div>

  <!-- Panel: Budget -->
  <div class="panel" id="panel-budget">
    <div class="budget-header">
      <h2>Ngân Sách Phòng Ban</h2>
      <button class="btn-reset-all" onclick="resetAll()">↺ Reset Tất Cả</button>
    </div>
    <div class="budget-grid" id="budget-grid">
      <div style="color:#fff;opacity:0.7;padding:20px">Đang tải...</div>
    </div>
  </div>

</div>

<div class="toast" id="toast"></div>

<script>
function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.innerHTML = (type==='success'?'✅':'❌') + ' ' + msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 4000);
}

function switchTab(tab, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + tab).classList.add('active');
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

/* ─── Pending ─── */
async function approve(id, btn) {
  btn.disabled = true; btn.textContent = 'Đang gửi...';
  try {
    const r = await fetch('/api/approve/' + id, {method:'POST'});
    const d = await r.json();
    if (r.ok) { showToast('Đã gửi APPROVE ' + id + ' tới Band!'); setTimeout(refresh, 2500); }
    else { showToast(d.error || 'Lỗi Band API', 'error'); btn.disabled=false; btn.textContent='✅ Duyệt'; }
  } catch { showToast('Lỗi kết nối','error'); btn.disabled=false; btn.textContent='✅ Duyệt'; }
}
function toggleRejectForm(id) {
  document.getElementById('reject-form-' + id).classList.toggle('show');
}
async function confirmReject(id) {
  const reason = (document.getElementById('reject-reason-' + id).value || '').trim() || 'Rejected by admin';
  const btn = document.getElementById('reject-confirm-btn-' + id);
  btn.disabled = true; btn.textContent = 'Đang gửi...';
  try {
    const r = await fetch('/api/reject/' + id, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({reason}),
    });
    const d = await r.json();
    if (r.ok) { showToast('Đã gửi REJECT ' + id + ' tới Band!'); setTimeout(refresh, 2500); }
    else { showToast(d.error || 'Lỗi Band API', 'error'); btn.disabled=false; btn.textContent='Xác Nhận'; }
  } catch { showToast('Lỗi kết nối','error'); btn.disabled=false; btn.textContent='Xác Nhận'; }
}

async function loadPending() {
  try {
    const r = await fetch('/api/pending');
    const d = await r.json();
    const list = document.getElementById('pending-list');
    const cnt  = document.getElementById('pending-count');
    if (!d.expenses || d.expenses.length === 0) {
      cnt.textContent = '';
      list.innerHTML = `<div class="empty"><div class="empty-icon">✅</div>
        <h3>Không có yêu cầu nào đang chờ</h3><p>Tất cả đã được xử lý</p></div>`;
      return;
    }
    cnt.textContent = '(' + d.expenses.length + ')';
    list.innerHTML = d.expenses.map(e => {
      const riskCls = e.risk_level === 'HIGH' ? 'tag-high' : 'tag-medium';
      const riskLbl = e.risk_level === 'HIGH' ? '🔴 HIGH RISK' : '🟡 MEDIUM RISK';
      const statusLbl = e.status === 'PENDING_CFO' ? 'Chờ CFO duyệt' : 'Chờ Manager duyệt';
      return `<div class="exp-card">
        <div class="exp-card-top">
          <div style="flex:1;min-width:0">
            <div class="exp-id">${e.id}</div>
            <div class="exp-desc">${e.description || e.expense_type || 'N/A'}</div>
            <div class="exp-meta">${e.requester||'—'} · ${e.department} · ${fmtDate(e.created_at)}</div>
          </div>
          <div><div class="exp-amount">$${(e.amount||0).toLocaleString()}</div></div>
        </div>
        <div class="exp-card-mid">
          <span class="tag ${riskCls}">${riskLbl}</span>
          <span class="tag tag-type">${e.expense_type||'other'}</span>
          <span class="tag tag-dept">${e.department}</span>
          ${e.vendor&&e.vendor!=='N/A'?`<span class="tag tag-dept">${e.vendor}</span>`:''}
          <span class="tag tag-status">${statusLbl}</span>
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
  } catch {}
}

/* ─── History ─── */
async function loadHistory() {
  try {
    const r = await fetch('/api/history');
    const d = await r.json();
    if (d.stats) {
      document.getElementById('s-pending').textContent  = d.stats.pending  || 0;
      document.getElementById('s-approved').textContent = d.stats.approved || 0;
      document.getElementById('s-rejected').textContent = d.stats.rejected || 0;
      document.getElementById('s-amount').textContent = '$' + (d.stats.total_approved_amount||0).toLocaleString();
    }
    const tbody = document.getElementById('history-body');
    if (!d.expenses || d.expenses.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:40px;color:#94a3b8">Chưa có giao dịch nào</td></tr>';
      return;
    }
    tbody.innerHTML = d.expenses.map(e => {
      const [scls,slbl] = statusMap[e.status] || ['b-pending', e.status];
      const rcls = e.risk_level==='HIGH'?'b-high':e.risk_level==='MEDIUM'?'b-medium':e.risk_level==='LOW'?'b-low':'';
      return `<tr>
        <td class="td-id">${e.id}</td>
        <td>${e.requester||'—'}</td>
        <td class="td-amount">$${(e.amount||0).toLocaleString()}</td>
        <td>${e.department}</td>
        <td>${e.expense_type||'—'}</td>
        <td class="td-desc" title="${e.description||''}">${(e.description||'').slice(0,45)||'—'}</td>
        <td>${rcls?`<span class="badge ${rcls}">${e.risk_level}</span>`:'—'}</td>
        <td><span class="badge ${scls}">${slbl}</span></td>
        <td class="td-date">${fmtDate(e.created_at)}</td>
      </tr>`;
    }).join('');
  } catch {}
}

/* ─── Live Feed ─── */
const agentMeta = {
  'budget-checker':    { label: 'Budget Checker',    cls: 'av-budget',   icon: '💰' },
  'policychecker':     { label: 'Policy Checker',    cls: 'av-policy',   icon: '📋' },
  'policy-checker':    { label: 'Policy Checker',    cls: 'av-policy',   icon: '📋' },
  'risk-evaluator':    { label: 'Risk Evaluator',    cls: 'av-risk',     icon: '⚠️' },
  'approval-notifier': { label: 'Approval Notifier', cls: 'av-approval', icon: '✅' },
};
function agentInfo(agentKey) {
  const k = (agentKey || '').toLowerCase();
  for (const [key, val] of Object.entries(agentMeta)) {
    if (k.includes(key)) return val;
  }
  return { label: agentKey || 'System', cls: 'av-system', icon: '⚙️' };
}
function actionColor(action) {
  if (!action) return '#64748b';
  const a = action.toUpperCase();
  if (a.includes('APPROVED') || a.includes('APPROVE')) return '#059669';
  if (a.includes('REJECTED') || a.includes('REJECT'))  return '#dc2626';
  if (a.includes('HIGH'))    return '#dc2626';
  if (a.includes('MEDIUM'))  return '#b45309';
  if (a.includes('LOW'))     return '#059669';
  if (a.includes('CREATED')) return '#4f46e5';
  return '#475569';
}

async function loadFeed() {
  try {
    const r = await fetch('/api/band-messages');
    const d = await r.json();
    const body = document.getElementById('feed-body');
    const cnt  = document.getElementById('feed-count');
    const ts   = document.getElementById('feed-ts');
    ts.textContent = 'Cập nhật: ' + new Date().toLocaleTimeString('vi-VN');

    if (!d.messages || d.messages.length === 0) {
      cnt.textContent = '';
      body.innerHTML = '<div class="feed-empty">Chưa có hoạt động nào. Gửi thử một expense request!</div>';
      return;
    }
    cnt.textContent = '(' + d.messages.length + ')';
    const wasAtBottom = body.scrollHeight - body.scrollTop <= body.clientHeight + 50;
    body.innerHTML = d.messages.map(m => {
      const info    = agentInfo(m.agent);
      const acolor  = actionColor(m.action);
      const expInfo = m.amount ? ` · ${m.expense_id} · $${Number(m.amount).toLocaleString()} · ${m.department}` : (m.expense_id ? ` · ${m.expense_id}` : '');
      return `<div class="msg-item">
        <div class="msg-avatar ${info.cls}">${info.icon}</div>
        <div class="msg-body">
          <div class="msg-sender">${info.label}<span style="font-weight:500;color:#94a3b8;margin-left:8px;font-size:0.7rem">${expInfo}</span></div>
          <div class="msg-content">
            <span style="background:#f1f5f9;padding:2px 8px;border-radius:6px;font-size:0.72rem;font-weight:700;color:${acolor}">${m.action}</span>
            ${m.details ? `<span style="margin-left:8px;color:#475569">${m.details.replace(/</g,'&lt;')}</span>` : ''}
          </div>
          <div class="msg-time">${fmtDate(m.timestamp)}</div>
        </div>
      </div>`;
    }).join('');
    if (wasAtBottom) body.scrollTop = body.scrollHeight;
  } catch {}
}

/* ─── Budget ─── */
async function loadBudget() {
  try {
    const r = await fetch('/api/budgets');
    const d = await r.json();
    const grid = document.getElementById('budget-grid');
    grid.innerHTML = d.budgets.map(b => {
      const used = b.monthly_limit - b.remaining;
      const pct  = Math.max(0, Math.min(100, (used / b.monthly_limit) * 100));
      const barCls = pct >= 90 ? 'bar-over' : pct >= 70 ? 'bar-warn' : 'bar-ok';
      return `<div class="budget-card">
        <div class="budget-dept">${b.department}</div>
        <div class="budget-row">
          <span class="budget-lbl">Hạn mức tháng</span>
          <span class="budget-val">$${b.monthly_limit.toLocaleString()}</span>
        </div>
        <div class="budget-row">
          <span class="budget-lbl">Đã sử dụng</span>
          <span class="budget-val" style="color:${pct>=90?'#dc2626':pct>=70?'#b45309':'#059669'}">
            $${used.toLocaleString()}
          </span>
        </div>
        <div class="budget-row">
          <span class="budget-lbl">Còn lại</span>
          <span class="budget-val">$${b.remaining.toLocaleString()}</span>
        </div>
        <div class="budget-bar-wrap"><div class="budget-bar ${barCls}" style="width:${pct}%"></div></div>
        <div class="budget-pct">${pct.toFixed(1)}% đã dùng</div>
        <button class="btn-reset-dept" onclick="resetDept('${b.department}', this)">↺ Reset ngân sách</button>
      </div>`;
    }).join('');
  } catch {}
}

async function resetDept(dept, btn) {
  btn.textContent = 'Đang reset...'; btn.disabled = true;
  try {
    const r = await fetch('/api/reset-budget/' + encodeURIComponent(dept), {method:'POST'});
    const d = await r.json();
    if (r.ok) { showToast('Đã reset ngân sách ' + dept); loadBudget(); }
    else { showToast(d.error || 'Lỗi reset', 'error'); }
  } catch { showToast('Lỗi kết nối', 'error'); }
  finally { btn.disabled = false; btn.textContent = '↺ Reset ngân sách'; }
}

async function resetAll() {
  if (!confirm('Reset ngân sách TẤT CẢ phòng ban về hạn mức ban đầu?')) return;
  try {
    const r = await fetch('/api/reset-all-budgets', {method:'POST'});
    const d = await r.json();
    if (r.ok) { showToast('Đã reset ngân sách tất cả phòng ban'); loadBudget(); }
    else showToast(d.error || 'Lỗi reset', 'error');
  } catch { showToast('Lỗi kết nối', 'error'); }
}

function refresh() { loadPending(); loadHistory(); loadFeed(); loadBudget(); }
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/pending")
def api_pending():
    with db._conn() as conn:
        rows = conn.execute("""
            SELECT id, requester, amount, department, expense_type,
                   description, vendor, status, risk_level, created_at
            FROM expenses
            WHERE status NOT IN ('APPROVED','REJECTED')
              AND (
                status IN ('PENDING_MANAGER','PENDING_CFO')
                OR risk_level IN ('MEDIUM','HIGH')
              )
            ORDER BY created_at DESC
        """).fetchall()
    return jsonify(expenses=[dict(r) for r in rows])


@app.route("/api/history")
def api_history():
    with db._conn() as conn:
        rows = conn.execute("""
            SELECT id, requester, amount, department, expense_type,
                   description, vendor, status, risk_level, created_at
            FROM expenses ORDER BY created_at DESC LIMIT 60
        """).fetchall()
        stats = dict(conn.execute("""
            SELECT
              COUNT(*) as total,
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
            FROM audit_log a
            LEFT JOIN expenses e ON a.expense_id = e.id
            ORDER BY a.id DESC LIMIT 80
        """).fetchall()
    msgs = list(reversed([dict(r) for r in rows]))
    return jsonify(messages=msgs)


@app.route("/api/budgets")
def api_budgets():
    return jsonify(budgets=db.get_all_budgets())


@app.route("/api/reset-budget/<dept>", methods=["POST"])
def api_reset_budget(dept):
    ok = db.reset_budget(dept)
    if ok:
        return jsonify(ok=True)
    return jsonify(ok=False, error="Department not found"), 404


@app.route("/api/reset-all-budgets", methods=["POST"])
def api_reset_all():
    db.reset_all_budgets()
    return jsonify(ok=True)


@app.route("/api/approve/<expense_id>", methods=["POST"])
def api_approve(expense_id):
    ok = _band_send(f"APPROVE {expense_id}")
    if ok:
        return jsonify(ok=True)
    return jsonify(ok=False, error="Không kết nối được Band API"), 502


@app.route("/api/reject/<expense_id>", methods=["POST"])
def api_reject(expense_id):
    data = request.get_json() or {}
    reason = (data.get("reason") or "Rejected by admin").strip()
    ok = _band_send(f"REJECT {expense_id} {reason}")
    if ok:
        return jsonify(ok=True)
    return jsonify(ok=False, error="Không kết nối được Band API"), 502


if __name__ == "__main__":
    print("Admin Panel → http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
