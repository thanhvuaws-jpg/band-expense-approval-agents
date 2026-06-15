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
<title>Yêu Cầu Chi Phí — Expense Request</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --primary-light: #e0e7ff;
  --success: #10b981;
  --success-bg: #d1fae5;
  --warning: #f59e0b;
  --warning-bg: #fef3c7;
  --danger: #ef4444;
  --danger-bg: #fee2e2;
  --bg: #f3f4f6;
  --card: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --radius: 16px;
  --shadow: 0 4px 24px rgba(0,0,0,0.07);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Plus Jakarta Sans', sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex; flex-direction: column;
  -webkit-font-smoothing: antialiased;
}

/* ── Header ── */
.header {
  padding: 20px 32px;
  display: flex; align-items: center; justify-content: space-between;
}
.logo { display: flex; align-items: center; gap: 12px; }
.logo-icon {
  width: 42px; height: 42px; background: rgba(255,255,255,0.2);
  border-radius: 12px; display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; backdrop-filter: blur(8px);
}
.logo h1 { font-size: 1.1rem; font-weight: 800; color: #fff; }
.logo p { font-size: 0.75rem; color: rgba(255,255,255,0.75); font-weight: 500; }
.live-badge {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.15); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.25);
  padding: 8px 16px; border-radius: 999px;
  color: #fff; font-size: 0.8rem; font-weight: 700;
}
.dot { width: 8px; height: 8px; background: #4ade80; border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(74,222,128,0.4); } 50%{ box-shadow:0 0 0 6px rgba(74,222,128,0); } }

/* ── Main ── */
.main {
  flex: 1; display: flex; align-items: flex-start; justify-content: center;
  padding: 0 16px 48px; gap: 24px; flex-wrap: wrap;
}

/* ── Form card ── */
.form-card {
  background: #fff; border-radius: 24px; padding: 40px;
  width: 100%; max-width: 560px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
  animation: slideUp 0.4s cubic-bezier(0.16,1,0.3,1);
}
@keyframes slideUp { from{transform:translateY(20px);opacity:0} to{transform:translateY(0);opacity:1} }

.form-title { font-size: 1.4rem; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.form-sub { font-size: 0.85rem; color: var(--muted); font-weight: 500; margin-bottom: 28px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.fg { display: flex; flex-direction: column; gap: 6px; }
.fg.full { grid-column: 1/-1; }
.fg label { font-size: 0.78rem; font-weight: 700; color: var(--text); text-transform: uppercase; letter-spacing: 0.5px; }
.fg input, .fg select {
  border: 1.5px solid var(--border); border-radius: 10px;
  padding: 11px 14px; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.9rem; font-weight: 500; color: var(--text);
  outline: none; transition: all 0.2s; background: #fff;
}
.fg input::placeholder { color: #94a3b8; }
.fg input:focus, .fg select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.btn-send {
  width: 100%; margin-top: 24px; padding: 14px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; border: none; border-radius: 12px;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1rem; font-weight: 700; cursor: pointer;
  box-shadow: 0 4px 16px rgba(79,70,229,0.35);
  transition: all 0.2s;
}
.btn-send:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(79,70,229,0.4); }
.btn-send:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.info-steps {
  margin-top: 24px; padding: 16px; background: var(--primary-light);
  border-radius: 12px; display: flex; flex-direction: column; gap: 8px;
}
.step { display: flex; align-items: center; gap: 10px; font-size: 0.8rem; font-weight: 600; color: var(--primary-hover); }
.step-num {
  width: 22px; height: 22px; background: var(--primary); color: #fff;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 0.7rem; font-weight: 800; flex-shrink: 0;
}

/* ── My requests card ── */
.requests-card {
  background: #fff; border-radius: 24px; padding: 32px;
  width: 100%; max-width: 560px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
  animation: slideUp 0.5s cubic-bezier(0.16,1,0.3,1);
}
.requests-title { font-size: 1rem; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.requests-sub { font-size: 0.8rem; color: var(--muted); margin-bottom: 20px; }

.req-item {
  padding: 14px 0; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.req-item:last-child { border-bottom: none; padding-bottom: 0; }
.req-info { flex: 1; min-width: 0; }
.req-id { font-size: 0.72rem; font-weight: 700; color: var(--primary); font-family: monospace; }
.req-desc { font-size: 0.85rem; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.req-meta { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
.req-right { text-align: right; flex-shrink: 0; }
.req-amount { font-size: 0.9rem; font-weight: 800; color: var(--text); }

.badge {
  display: inline-block; padding: 4px 10px; border-radius: 999px;
  font-size: 0.7rem; font-weight: 700; margin-top: 4px;
}
.b-approved { background: var(--success-bg); color: #059669; }
.b-pending  { background: var(--warning-bg); color: #b45309; }
.b-rejected { background: var(--danger-bg);  color: #dc2626; }
.b-cfo      { background: #f3e8ff; color: #7c3aed; }
.b-manager  { background: var(--primary-light); color: var(--primary-hover); }

.empty { text-align: center; padding: 32px 0; color: var(--muted); font-size: 0.85rem; font-weight: 600; }

/* ── Toast ── */
.toast {
  position: fixed; bottom: 28px; right: 28px; z-index: 999;
  padding: 14px 20px; border-radius: 12px; background: #fff;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  font-size: 0.9rem; font-weight: 700; color: var(--text);
  display: none; align-items: center; gap: 10px;
  animation: slideT 0.3s cubic-bezier(0.16,1,0.3,1);
}
.toast.show { display: flex; }
.toast.success { border-left: 5px solid var(--success); }
.toast.error   { border-left: 5px solid var(--danger); }
@keyframes slideT { from{transform:translateX(40px);opacity:0} to{transform:translateX(0);opacity:1} }
</style>
</head>
<body>

<header class="header">
  <div class="logo">
    <div class="logo-icon">💼</div>
    <div>
      <h1>Expense Request</h1>
      <p>AI-Powered Approval System</p>
    </div>
  </div>
  <div class="live-badge"><span class="dot"></span> AI Agents Online</div>
</header>

<div class="main">

  <!-- Form -->
  <div class="form-card">
    <div class="form-title">Tạo Yêu Cầu Chi Phí</div>
    <div class="form-sub">Điền đầy đủ thông tin bên dưới. AI sẽ xử lý và phản hồi trong Band.</div>

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
      <div class="step"><span class="step-num">1</span> AI kiểm tra ngân sách phòng ban</div>
      <div class="step"><span class="step-num">2</span> Kiểm tra quy định công ty</div>
      <div class="step"><span class="step-num">3</span> Đánh giá rủi ro & tự động duyệt hoặc chuyển manager</div>
    </div>
  </div>

  <!-- My requests -->
  <div class="requests-card">
    <div class="requests-title">Yêu Cầu Gần Đây</div>
    <div class="requests-sub">Tự động cập nhật mỗi 5 giây</div>
    <div id="req-list"><div class="empty">Chưa có yêu cầu nào</div></div>
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
      method: 'POST',
      headers: {'Content-Type':'application/json'},
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
    } else {
      showToast(d.error || 'Gửi thất bại', 'error');
    }
  } catch(e) {
    showToast('Lỗi kết nối', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Gửi Yêu Cầu';
  }
}

const statusMap = {
  APPROVED:        ['b-approved', 'Đã Duyệt'],
  REJECTED:        ['b-rejected', 'Từ Chối'],
  PENDING:         ['b-pending',  'Đang Xử Lý'],
  PENDING_MANAGER: ['b-manager',  'Chờ Manager'],
  PENDING_CFO:     ['b-cfo',      'Chờ CFO'],
};

async function loadRequests() {
  try {
    const r = await fetch('/api/data');
    const d = await r.json();
    const list = document.getElementById('req-list');
    if (!d.expenses || d.expenses.length === 0) {
      list.innerHTML = '<div class="empty">Chưa có yêu cầu nào</div>'; return;
    }
    list.innerHTML = d.expenses.map(e => {
      const [cls, label] = statusMap[e.status] || ['b-pending', e.status];
      return `<div class="req-item">
        <div class="req-info">
          <div class="req-id">${e.id}</div>
          <div class="req-desc">${e.department} · ${e.requester || '—'}</div>
          <div class="req-meta">${(e.description||'').slice(0,40) || e.expense_type || ''}</div>
        </div>
        <div class="req-right">
          <div class="req-amount">$${(e.amount||0).toLocaleString()}</div>
          <div class="badge ${cls}">${label}</div>
        </div>
      </div>`;
    }).join('');
  } catch(e) {}
}

loadRequests();
setInterval(loadRequests, 5000);
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
                "SELECT id, requester, amount, department, expense_type, description, risk_level, status "
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