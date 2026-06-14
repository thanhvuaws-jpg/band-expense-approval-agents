"""
Real-time web dashboard for the Expense Approval System.
Run standalone: python dashboard.py
Auto-refreshes every 3 seconds. Submit form sends directly to Band room.
"""

import db
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Expense Approval — Live Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  /* Corporate Light Theme Colors */
  --bg-app: #f3f4f6;
  --bg-card: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  
  /* Brand & Status Colors */
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --primary-light: #e0e7ff;
  --success: #10b981;
  --success-bg: #d1fae5;
  --warning: #f59e0b;
  --warning-bg: #fef3c7;
  --danger: #ef4444;
  --danger-bg: #fee2e2;
  
  --radius: 16px;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.03);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Plus Jakarta Sans', sans-serif;
  background: var(--bg-app);
  color: var(--text-main);
  min-height: 100vh;
  overflow-x: hidden;
  -webkit-font-smoothing: antialiased;
}

/* ── Header ── */
.header {
  position: sticky; top: 0; z-index: 100;
  padding: 16px 32px;
  display: flex; align-items: center; justify-content: space-between;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.header-left h1 {
  font-size: 1.25rem; font-weight: 800; letter-spacing: -0.02em;
  color: var(--text-main);
  display: flex; align-items: center; gap: 8px;
}
.header-left p { font-size: 0.8rem; color: var(--text-muted); font-weight: 500; }
.live-dot {
  display: inline-block; width: 8px; height: 8px;
  background: var(--success); border-radius: 50%;
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%,100%{ box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
  50%    { box-shadow: 0 0 0 6px rgba(16,185,129,0); }
}

.btn-submit {
  padding: 10px 24px; border-radius: 10px; border: none; cursor: pointer;
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.875rem; font-weight: 700;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  transition: all 0.2s ease;
}
.btn-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
}

/* ── Main layout ── */
.main { padding: 32px; max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }

/* ── Stat cards ── */
.stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 20px; }
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px;
  box-shadow: var(--shadow-sm);
  display: flex; flex-direction: column; gap: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }

.stat-header { display: flex; justify-content: space-between; align-items: flex-start; }
.stat-icon { 
  width: 40px; height: 40px; border-radius: 12px; 
  display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
}
.stat-card.total .stat-icon { background: var(--primary-light); color: var(--primary); }
.stat-card.approved .stat-icon { background: var(--success-bg); color: var(--success); }
.stat-card.pending .stat-icon { background: var(--warning-bg); color: var(--warning); }
.stat-card.rejected .stat-icon { background: var(--danger-bg); color: var(--danger); }

.stat-num  { font-size: 2rem; font-weight: 800; color: var(--text-main); line-height: 1; }
.stat-lbl  { font-size: 0.85rem; color: var(--text-muted); font-weight: 600; }

/* ── Pipeline ── */
.pipeline {
  display: flex; align-items: center; justify-content: space-between;
  padding: 24px 32px; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.pipeline-title { font-size: 0.9rem; font-weight: 700; color: var(--text-main); margin-bottom: 16px; width: 100%; position: absolute; top: -30px;}
.pipe-agent {
  display: flex; flex-direction: column; align-items: center; gap: 10px; flex: 1; z-index: 2;
}
.pipe-icon {
  width: 50px; height: 50px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; font-weight: 700; background: #fff;
  box-shadow: var(--shadow-md); border: 1px solid var(--border);
}
.pipe-icon.a1 { border-bottom: 3px solid #4f46e5; }
.pipe-icon.a2 { border-bottom: 3px solid #10b981; }
.pipe-icon.a3 { border-bottom: 3px solid #f59e0b; }
.pipe-icon.a4 { border-bottom: 3px solid #8b5cf6; }
.pipe-name { font-size: 0.75rem; color: var(--text-main); font-weight: 700; text-align: center; line-height: 1.3;}
.pipe-arrow { 
  flex-grow: 1; height: 2px; background: #cbd5e1; position: relative; margin: 0 10px; top: -15px; z-index: 1;
}
.pipe-arrow::after {
  content: '▶'; position: absolute; right: -5px; top: -7px; color: #cbd5e1; font-size: 12px;
}
.pipe-arrow.text { text-align: center; background: transparent; color: var(--text-muted); font-size: 0.75rem; font-weight: 600; top: -20px; }
.pipe-arrow.text::after { display: none; }

/* ── Grid ── */
.grid { display: grid; grid-template-columns: 1fr 2fr; gap: 24px; align-items: start; }

/* ── Cards ── */
.card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow-sm);
}
.card-title {
  font-size: 1rem; color: var(--text-main); font-weight: 700; margin-bottom: 20px;
  display: flex; align-items: center; gap: 8px;
}
.card-title .icon { font-size: 1.2rem; }

/* ── Budget bars ── */
.dept { margin-bottom: 20px; }
.dept:last-child { margin-bottom: 0; }
.dept-row { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px; }
.dept-name { font-size: 0.9rem; font-weight: 700; color: var(--text-main); }
.dept-meta { font-size: 0.8rem; color: var(--text-muted); font-weight: 500; }
.dept-pct  { font-size: 0.8rem; font-weight: 800; margin-left: 6px; }
.bar-track { background: #e2e8f0; border-radius: 8px; height: 8px; overflow: hidden; }
.bar-fill  {
  height: 100%; border-radius: 8px;
  transition: width 0.8s cubic-bezier(.4,0,.2,1);
}
.bar-ok        { background: var(--success); }
.bar-warning   { background: var(--warning); }
.bar-critical  { background: var(--danger); }
.pct-ok        { color: var(--success); }
.pct-warning   { color: var(--warning); }
.pct-critical  { color: var(--danger); }

/* ── Table ── */
.table-wrap { overflow-x: auto; margin: -8px; padding: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
thead th {
  padding: 12px 16px; text-align: left;
  font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--text-muted); font-weight: 700;
  border-bottom: 2px solid var(--border);
}
tbody tr {
  border-bottom: 1px solid var(--border);
  transition: background 0.2s;
}
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: #f8fafc; }
td { padding: 14px 16px; vertical-align: middle; font-weight: 500; }
td:first-child { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--primary); font-weight: 700; }

.badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 6px 12px; border-radius: 999px;
  font-size: 0.75rem; font-weight: 700;
}
.badge-approved  { background: var(--success-bg); color: #059669; }
.badge-pending   { background: var(--warning-bg); color: #d97706; }
.badge-rejected  { background: var(--danger-bg);  color: #dc2626; }
.badge-manager   { background: var(--primary-light); color: var(--primary-hover); }
.badge-cfo       { background: #f3e8ff; color: #7e22ce; }

.risk-LOW    { color: #059669; font-weight: 800; background: #d1fae5; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; }
.risk-MEDIUM { color: #d97706; font-weight: 800; background: #fef3c7; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; }
.risk-HIGH   { color: #dc2626; font-weight: 800; background: #fee2e2; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; }
.risk-none   { color: var(--text-muted); }

/* ── Audit Timeline ── */
.audit-list { 
  display: flex; flex-direction: column; position: relative; padding-left: 24px; margin-top: 10px;
}
.audit-list::before {
  content: ''; position: absolute; left: 7px; top: 8px; bottom: 8px; width: 2px; background: #e2e8f0;
}
.audit-item {
  position: relative; padding-bottom: 20px; animation: fadeIn 0.4s ease;
}
.audit-item:last-child { padding-bottom: 0; }
.audit-item::before {
  content: ''; position: absolute; left: -22px; top: 4px; width: 12px; height: 12px;
  border-radius: 50%; background: var(--primary); border: 2px solid #fff; box-shadow: 0 0 0 2px var(--primary-light);
}
@keyframes fadeIn { from{ opacity:0; transform:translateX(-10px); } to{ opacity:1; transform:translateX(0); } }

.audit-header { display: flex; justify-content: space-between; margin-bottom: 4px; align-items: center; }
.audit-agent { font-size: 0.8rem; font-weight: 700; color: var(--text-main); }
.audit-time  { font-size: 0.7rem; color: var(--text-muted); font-weight: 600; }
.audit-body  { font-size: 0.85rem; color: var(--text-main); background: #f8fafc; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); display: inline-block; width: 100%;}
.audit-detail{ color: var(--text-muted); font-size: 0.75rem; margin-top: 4px; font-weight: 500; }

.updated-bar {
  text-align: right; font-size: 0.75rem; color: var(--text-muted); font-weight: 600;
  padding-top: 16px; border-top: 1px solid var(--border); margin-top: 16px;
}

/* ── Submit Form Modal (Corporate Style) ── */
.overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px);
  display: none; align-items: center; justify-content: center;
}
.overlay.open { display: flex; animation: fadeInOverlay 0.2s ease; }
@keyframes fadeInOverlay { from{opacity:0} to{opacity:1} }

.modal {
  background: #fff;
  border-radius: 20px; padding: 0;
  width: 540px; max-width: 95vw;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}
@keyframes slideUp { from{transform:translateY(30px);opacity:0} to{transform:translateY(0);opacity:1} }

.modal-header {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  padding: 24px 32px; color: #fff;
}
.modal-header h2 { font-size: 1.25rem; font-weight: 800; margin-bottom: 4px; }
.modal-header p { font-size: 0.85rem; opacity: 0.9; }

.modal-body { padding: 32px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.form-group { display: flex; flex-direction: column; gap: 8px; }
.form-group.full { grid-column: 1/-1; }
.form-group label { font-size: 0.8rem; color: var(--text-main); font-weight: 700; }
.form-group input, .form-group select {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 10px; padding: 12px 16px;
  color: var(--text-main); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; font-weight: 500;
  outline: none; transition: all 0.2s;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.02);
}
.form-group input::placeholder { color: #94a3b8; }
.form-group input:focus, .form-group select:focus {
  border-color: var(--primary); 
  box-shadow: 0 0 0 3px var(--primary-light);
}

.form-actions { display: flex; gap: 12px; margin-top: 32px; }
.btn-cancel {
  flex: 1; padding: 12px; border-radius: 10px;
  background: #f1f5f9; border: 1px solid #cbd5e1;
  color: var(--text-main); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; font-weight: 700;
  cursor: pointer; transition: all 0.2s;
}
.btn-cancel:hover { background: #e2e8f0; }
.btn-send {
  flex: 2; padding: 12px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.9rem; font-weight: 700;
  cursor: pointer; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  transition: all 0.2s;
}
.btn-send:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4); }
.btn-send:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.toast {
  position: fixed; bottom: 32px; right: 32px; z-index: 300;
  padding: 16px 24px; border-radius: 12px;
  font-size: 0.9rem; font-weight: 700;
  display: none; animation: slideToast 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  max-width: 400px; box-shadow: var(--shadow-lg);
  display: flex; align-items: center; gap: 10px;
}
.toast.show { display: flex; }
.toast.success { background: #fff; border-left: 6px solid var(--success); color: var(--text-main); }
.toast.error   { background: #fff; border-left: 6px solid var(--danger);  color: var(--text-main); }
@keyframes slideToast { from{transform:translateX(50px);opacity:0} to{transform:translateX(0);opacity:1} }

</style>
</head>
<body>

<header class="header">
  <div class="header-left">
    <h1><span class="live-dot"></span> Expense Approval System</h1>
    <p>Automated Corporate Workflow &nbsp;·&nbsp; AI Agents Active</p>
  </div>
  <button class="btn-submit" onclick="openModal()">+ TẠO ĐỀ XUẤT</button>
</header>

<main class="main">

  <!-- Stats -->
  <div class="stats" id="stats">
    <div class="stat-card total">
      <div class="stat-header">
        <div>
          <div class="stat-lbl">Tổng Đề Xuất</div>
          <div class="stat-num" id="stat-total">—</div>
        </div>
        <div class="stat-icon">📊</div>
      </div>
    </div>
    <div class="stat-card approved">
      <div class="stat-header">
        <div>
          <div class="stat-lbl">Đã Duyệt</div>
          <div class="stat-num" id="stat-approved">—</div>
        </div>
        <div class="stat-icon">✅</div>
      </div>
    </div>
    <div class="stat-card pending">
      <div class="stat-header">
        <div>
          <div class="stat-lbl">Đang Chờ</div>
          <div class="stat-num" id="stat-pending">—</div>
        </div>
        <div class="stat-icon">⏳</div>
      </div>
    </div>
    <div class="stat-card rejected">
      <div class="stat-header">
        <div>
          <div class="stat-lbl">Từ Chối</div>
          <div class="stat-num" id="stat-rejected">—</div>
        </div>
        <div class="stat-icon">❌</div>
      </div>
    </div>
  </div>

  <!-- Pipeline -->
  <div style="position: relative; margin-top: 10px;">
    <div class="pipeline">
      <div class="pipe-agent"><div class="pipe-icon a1">💰</div><div class="pipe-name">Kiểm Tra<br>Ngân Sách</div></div>
      <div class="pipe-arrow"></div>
      <div class="pipe-agent"><div class="pipe-icon a2">📋</div><div class="pipe-name">Quy Định<br>Công Ty</div></div>
      <div class="pipe-arrow"></div>
      <div class="pipe-agent"><div class="pipe-icon a3">⚖️</div><div class="pipe-name">Đánh Giá<br>Rủi Ro</div></div>
      <div class="pipe-arrow text">Rủi ro thấp</div>
      <div class="pipe-agent"><div class="pipe-icon a4">🔔</div><div class="pipe-name">Thông Báo<br>Phê Duyệt</div></div>
    </div>
  </div>

  <!-- Budget + Expenses -->
  <div class="grid">
    <div class="card">
      <div class="card-title"><span class="icon">📈</span> Ngân Sách Phòng Ban</div>
      <div id="budgets"></div>
    </div>
    <div class="card">
      <div class="card-title"><span class="icon">🧾</span> Đề Xuất Gần Đây</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Mã ĐX</th><th>Người Yêu Cầu</th><th>Số Tiền</th><th>Phòng Ban</th><th>Rủi Ro</th><th>Trạng Thái</th></tr>
          </thead>
          <tbody id="expenses"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Audit -->
  <div class="card">
    <div class="card-title"><span class="icon">🔍</span> Nhật Ký Hoạt Động (Audit Trail)</div>
    <div class="audit-list" id="audit"></div>
    <div class="updated-bar" id="updated"></div>
  </div>

</main>

<!-- Submit modal -->
<div class="overlay" id="overlay" onclick="closeOnBg(event)">
  <div class="modal">
    <div class="modal-header">
      <h2>Tạo Đề Xuất Chi Tiêu</h2>
      <p>Thông tin sẽ được xử lý tự động bởi AI Workflow.</p>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group">
          <label>Người Yêu Cầu</label>
          <input type="text" id="f-requester" placeholder="VD: Nguyễn Văn A">
        </div>
        <div class="form-group">
          <label>Số Tiền (USD)</label>
          <input type="number" id="f-amount" placeholder="VD: 500" min="1">
        </div>
        <div class="form-group">
          <label>Phòng Ban</label>
          <select id="f-dept">
            <option value="Engineering">Kỹ Thuật (Engineering)</option>
            <option value="Marketing">Marketing</option>
            <option value="HR">Nhân Sự (HR)</option>
            <option value="Operations">Vận Hành (Operations)</option>
            <option value="Finance">Tài Chính (Finance)</option>
            <option value="Sales">Kinh Doanh (Sales)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Nhà Cung Cấp</label>
          <input type="text" id="f-vendor" placeholder="Amazon, Microsoft...">
        </div>
        <div class="form-group full">
          <label>Mô Tả Chi Tiết</label>
          <input type="text" id="f-desc" placeholder="Mua bản quyền phần mềm AWS, văn phòng phẩm...">
        </div>
      </div>
      <div class="form-actions">
        <button class="btn-cancel" onclick="closeModal()">Hủy</button>
        <button class="btn-send" id="btn-send" onclick="submitExpense()">🚀 Gửi Yêu Cầu</button>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ── Modal ──────────────────────────────────────────────
function openModal()  { document.getElementById('overlay').classList.add('open'); }
function closeModal() { document.getElementById('overlay').classList.remove('open'); }
function closeOnBg(e) { if(e.target===document.getElementById('overlay')) closeModal(); }

function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  const icon = type === 'success' ? '✅' : '❌';
  t.innerHTML = `<span>${icon}</span> <span>${msg}</span>`; 
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 4000);
}

async function submitExpense() {
  const requester = document.getElementById('f-requester').value.trim();
  const amount    = document.getElementById('f-amount').value.trim();
  const dept      = document.getElementById('f-dept').value;
  const vendor    = document.getElementById('f-vendor').value.trim() || 'N/A';
  const desc      = document.getElementById('f-desc').value.trim();

  if (!requester || !amount || !desc) {
    showToast('Vui lòng nhập Tên, Số tiền và Mô tả.', 'error'); return;
  }

  const btn = document.getElementById('btn-send');
  btn.disabled = true; btn.textContent = 'Đang gửi…';

  try {
    const res = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requester, amount, department: dept, vendor, description: desc })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Gửi thành công! Đang chờ AI xử lý…', 'success');
      closeModal();
      document.getElementById('f-requester').value = '';
      document.getElementById('f-amount').value = '';
      document.getElementById('f-desc').value = '';
      document.getElementById('f-vendor').value = '';
    } else {
      showToast(data.error || 'Gửi thất bại', 'error');
    }
  } catch(e) {
    showToast('Lỗi kết nối mạng', 'error');
  } finally {
    btn.disabled = false; btn.textContent = '🚀 Gửi Yêu Cầu';
  }
}

// ── Dashboard refresh ──────────────────────────────────
async function refresh() {
  try {
    const r = await fetch('/api/data');
    const d = await r.json();

    // Stats
    document.getElementById('stat-total').textContent = d.stats.total ?? 0;
    document.getElementById('stat-approved').textContent = d.stats.approved ?? 0;
    document.getElementById('stat-pending').textContent = d.stats.pending ?? 0;
    document.getElementById('stat-rejected').textContent = d.stats.rejected ?? 0;

    // Budgets
    document.getElementById('budgets').innerHTML = d.budgets.map(b => {
      const pct = Math.round(b.remaining / b.monthly_limit * 100);
      const cls = pct > 30 ? 'bar-ok' : pct > 10 ? 'bar-warning' : 'bar-critical';
      const pc  = pct > 30 ? 'pct-ok' : pct > 10 ? 'pct-warning' : 'pct-critical';
      return `<div class="dept">
        <div class="dept-row">
          <span class="dept-name">${b.department}</span>
          <span class="dept-meta">$${b.remaining.toLocaleString()} / $${b.monthly_limit.toLocaleString()} <span class="${pc}">${pct}%</span></span>
        </div>
        <div class="bar-track"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div>
      </div>`;
    }).join('');

    // Expenses
    const statusBadge = {
      APPROVED:        '<span class="badge badge-approved">Đã Duyệt</span>',
      REJECTED:        '<span class="badge badge-rejected">Từ Chối</span>',
      PENDING:         '<span class="badge badge-pending">Chờ Duyệt</span>',
      PENDING_MANAGER: '<span class="badge badge-manager">Chờ Quản Lý</span>',
      PENDING_CFO:     '<span class="badge badge-cfo">Chờ CFO</span>',
    };
    document.getElementById('expenses').innerHTML = d.expenses.map(e => {
      const badge = statusBadge[e.status] || `<span class="badge badge-pending">${e.status}</span>`;
      const risk  = e.risk_level ? `<span class="risk-${e.risk_level}">${e.risk_level}</span>` : '<span class="risk-none">Chưa rõ</span>';
      return `<tr>
        <td>#${e.id}</td>
        <td>${e.requester || '—'}</td>
        <td style="color:var(--text-main);">$${(e.amount||0).toLocaleString()}</td>
        <td style="color:var(--text-muted); font-weight:600;">${e.department || '—'}</td>
        <td>${risk}</td>
        <td>${badge}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted)">Chưa có yêu cầu nào — Hãy tạo đề xuất mới!</td></tr>';

    // Audit Timeline
    const agentColor = t => {
      if (t.includes('budget'))  return '#4f46e5';
      if (t.includes('policy'))  return '#10b981';
      if (t.includes('risk'))    return '#f59e0b';
      if (t.includes('approval'))return '#8b5cf6';
      return '#64748b';
    };
    
    document.getElementById('audit').innerHTML = d.audit.map(a => {
      const ag = a.agent || 'Hệ Thống';
      return `<div class="audit-item">
        <div class="audit-header">
          <span class="audit-agent" style="color:${agentColor(ag.toLowerCase())}">${ag}</span>
          <span class="audit-time">${a.timestamp.slice(0,19).replace('T',' ')}</span>
        </div>
        <div class="audit-body">
          <div style="font-weight: 700;">${a.action}</div>
          ${a.details ? `<div class="audit-detail">${a.details}</div>` : ''}
        </div>
      </div>`;
    }).join('') || '<div style="color:var(--text-muted);padding:16px 0;font-size:0.85rem">Chưa có lịch sử hoạt động</div>';

    document.getElementById('updated').textContent = 'Cập nhật lần cuối: ' + new Date().toLocaleTimeString('vi-VN');
  } catch(e) {
    console.error("Refresh error:", e);
  }
}

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/data")
def api_data():
    budgets = db.get_all_budgets()
    with db._conn() as conn:
        expenses = [
            dict(r) for r in conn.execute(
                "SELECT id, requester, amount, department, risk_level, status "
                "FROM expenses ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        ]
        audit = [
            dict(r) for r in conn.execute(
                "SELECT agent, action, details, timestamp FROM audit_log "
                "ORDER BY id DESC LIMIT 40"
            ).fetchall()
        ]
        row = conn.execute("""
            SELECT
              COUNT(*) as total,
              SUM(CASE WHEN status='APPROVED' THEN 1 ELSE 0 END) as approved,
              SUM(CASE WHEN status='REJECTED' THEN 1 ELSE 0 END) as rejected,
              SUM(CASE WHEN status NOT IN ('APPROVED','REJECTED') THEN 1 ELSE 0 END) as pending
            FROM expenses
        """).fetchone()
        stats = dict(row)
    return jsonify(budgets=budgets, expenses=expenses, audit=audit, stats=stats)

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
    return jsonify(ok=True, queued_id=row_id, message=msg)

def run_dashboard():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    db.init_db()
    print("Dashboard UI Mới → http://localhost:5000")
    run_dashboard()