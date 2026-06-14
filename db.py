"""SQLite database layer for Expense Approval System."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "database.db"

DEPARTMENTS = {
    "Engineering": (10000, 8500),
    "Marketing":   (5000,  3200),
    "HR":          (3000,  2800),
    "Operations":  (7000,  6100),
    "Finance":     (4000,  3500),
    "Sales":       (6000,  4800),
}

FLAGGED_KEYWORDS = {"personal", "gift", "alcohol", "entertainment", "casino", "gambling"}

POLICY_RULES = {
    "travel":   {"review_above": 500,  "msg": "Travel >$500 requires 2-week advance notice"},
    "software": {"block_above":  1000, "msg": "Software >$1,000 requires IT pre-approval"},
    "hardware": {"review_above": 500,  "msg": "Hardware >$500 requires asset tracking"},
}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS budgets (
                department    TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL,
                remaining     REAL NOT NULL,
                last_reset    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id           TEXT PRIMARY KEY,
                requester    TEXT,
                amount       REAL,
                department   TEXT,
                expense_type TEXT,
                description  TEXT,
                vendor       TEXT DEFAULT '',
                status       TEXT DEFAULT 'PENDING',
                risk_level   TEXT DEFAULT '',
                budget_ok    INTEGER DEFAULT 1,
                policy_notes TEXT DEFAULT '',
                risk_notes   TEXT DEFAULT '',
                created_at   TEXT,
                updated_at   TEXT,
                room_id      TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id TEXT,
                agent      TEXT,
                action     TEXT,
                details    TEXT,
                timestamp  TEXT
            );

            CREATE TABLE IF NOT EXISTS pending_sends (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                message    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent       INTEGER DEFAULT 0
            );
        """)
        if conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0] == 0:
            now = datetime.now().isoformat()
            conn.executemany(
                "INSERT INTO budgets VALUES (?,?,?,?)",
                [(d, limit, remaining, now) for d, (limit, remaining) in DEPARTMENTS.items()],
            )


# ── Budget ────────────────────────────────────────────────────────────────────

def get_budget(department: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT department, monthly_limit, remaining FROM budgets WHERE department=?",
            (department,),
        ).fetchone()
    return dict(row) if row else None


def get_all_budgets() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT department, monthly_limit, remaining FROM budgets").fetchall()
    return [dict(r) for r in rows]


def deduct_budget(department: str, amount: float) -> bool:
    with _conn() as conn:
        conn.execute(
            "UPDATE budgets SET remaining = remaining - ? WHERE department = ?",
            (amount, department),
        )
    return True


# ── Expenses ──────────────────────────────────────────────────────────────────

def create_expense(
    requester: str,
    amount: float,
    department: str,
    expense_type: str,
    description: str,
    vendor: str = "",
    room_id: str = "",
) -> str:
    expense_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now().isoformat()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO expenses
               (id, requester, amount, department, expense_type, description,
                vendor, status, created_at, updated_at, room_id)
               VALUES (?,?,?,?,?,?,?,'PENDING',?,?,?)""",
            (expense_id, requester, amount, department, expense_type,
             description, vendor, now, now, room_id),
        )
    return expense_id


def get_expense(expense_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
    return dict(row) if row else None


def update_expense(expense_id: str, **fields) -> bool:
    if not fields:
        return False
    fields["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [expense_id]
    with _conn() as conn:
        conn.execute(f"UPDATE expenses SET {sets} WHERE id=?", vals)
    return True


def approve_expense(expense_id: str, approved_by: str = "system") -> bool:
    row = get_expense(expense_id)
    if not row:
        return False
    update_expense(expense_id, status="APPROVED")
    deduct_budget(row["department"], row["amount"])
    log_audit(expense_id, approved_by, "APPROVED", f"${row['amount']} deducted from {row['department']}")
    return True


def reject_expense(expense_id: str, reason: str, rejected_by: str = "system") -> bool:
    if not get_expense(expense_id):
        return False
    update_expense(expense_id, status="REJECTED", risk_notes=reason)
    log_audit(expense_id, rejected_by, "REJECTED", reason)
    return True


# ── Policy check ──────────────────────────────────────────────────────────────

def check_policy(expense_type: str, amount: float, description: str, vendor: str = "") -> dict:
    issues = []
    flags = []

    rule = POLICY_RULES.get(expense_type.lower(), {})
    if "block_above" in rule and amount > rule["block_above"]:
        issues.append(rule["msg"])
    elif "review_above" in rule and amount > rule["review_above"]:
        flags.append(rule["msg"])

    if amount > 5000:
        issues.append("Single expense >$5,000 requires CFO sign-off")

    desc_words = set(description.lower().split())
    found = desc_words & FLAGGED_KEYWORDS
    if found:
        issues.append(f"Flagged terms in description: {', '.join(found)}")

    if issues:
        status = "NON-COMPLIANT"
    elif flags:
        status = "CONDITIONAL"
    else:
        status = "COMPLIANT"

    return {"status": status, "issues": issues, "flags": flags}


# ── Audit ─────────────────────────────────────────────────────────────────────

def log_audit(expense_id: str, agent: str, action: str, details: str = "") -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (expense_id, agent, action, details, timestamp) VALUES (?,?,?,?,?)",
            (expense_id, agent, action, details, datetime.now().isoformat()),
        )


def get_audit_trail(expense_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT agent, action, details, timestamp FROM audit_log WHERE expense_id=? ORDER BY id",
            (expense_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Pending sends (dashboard → main.py queue) ─────────────────────────────────

def queue_message(message: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO pending_sends (message, created_at) VALUES (?,?)",
            (message, datetime.now().isoformat()),
        )
    return cur.lastrowid


def pop_pending_messages() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, message FROM pending_sends WHERE sent=0 ORDER BY id"
        ).fetchall()
        if rows:
            ids = [r["id"] for r in rows]
            conn.execute(
                f"UPDATE pending_sends SET sent=1 WHERE id IN ({','.join('?'*len(ids))})",
                ids,
            )
    return [dict(r) for r in rows]
