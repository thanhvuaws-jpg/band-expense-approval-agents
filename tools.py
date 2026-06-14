"""LangChain tools wrapping the database layer."""

from langchain_core.tools import tool
import db


@tool
def check_department_budget(department: str) -> str:
    """Check the remaining monthly budget for a department.
    Returns budget limit, remaining amount, and whether it can cover a request."""
    row = db.get_budget(department)
    if not row:
        depts = ", ".join(db.DEPARTMENTS.keys())
        return f"Department '{department}' not found. Available: {depts}"
    pct = (row["remaining"] / row["monthly_limit"]) * 100
    return (
        f"Department: {row['department']}\n"
        f"Monthly Limit:  ${row['monthly_limit']:,.0f}\n"
        f"Remaining:      ${row['remaining']:,.0f}  ({pct:.0f}% left)\n"
        f"Status: {'WITHIN BUDGET' if row['remaining'] > 0 else 'BUDGET EXHAUSTED'}"
    )


@tool
def get_all_department_budgets() -> str:
    """Get a summary of all department budgets."""
    rows = db.get_all_budgets()
    lines = ["ALL DEPARTMENT BUDGETS:"]
    for r in rows:
        pct = (r["remaining"] / r["monthly_limit"]) * 100
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(
            f"  {r['department']:12} [{bar}] ${r['remaining']:>7,.0f} / ${r['monthly_limit']:,.0f}"
        )
    return "\n".join(lines)


@tool
def create_expense_record(
    requester: str,
    amount: float,
    department: str,
    expense_type: str,
    description: str,
    vendor: str = "",
) -> str:
    """Create a new expense record in the database. Returns the unique expense ID (e.g. EXP-A1B2C3D4).
    Always call this first when processing a new expense request."""
    expense_id = db.create_expense(
        requester=requester,
        amount=amount,
        department=department,
        expense_type=expense_type,
        description=description,
        vendor=vendor,
    )
    db.log_audit(expense_id, "budget-checker", "RECORD_CREATED",
                 f"${amount} | {department} | {expense_type}")
    return f"Expense record created successfully. ID: {expense_id}"


@tool
def check_policy_compliance(expense_type: str, amount: float, description: str, vendor: str = "") -> str:
    """Check if an expense complies with company policies.
    Returns compliance status, issues that block approval, and flags that need review."""
    result = db.check_policy(expense_type, amount, description, vendor)
    lines = [f"Policy Status: {result['status']}"]
    if result["issues"]:
        lines.append("BLOCKING ISSUES:")
        for issue in result["issues"]:
            lines.append(f"  ✗ {issue}")
    if result["flags"]:
        lines.append("REVIEW FLAGS:")
        for flag in result["flags"]:
            lines.append(f"  ⚠ {flag}")
    if not result["issues"] and not result["flags"]:
        lines.append("  ✓ No policy issues found")
    return "\n".join(lines)


@tool
def update_expense_status(
    expense_id: str,
    status: str,
    risk_level: str = "",
    notes: str = "",
) -> str:
    """Update the status of an expense record.
    Status options: PENDING, PENDING_MANAGER, PENDING_CFO, APPROVED, REJECTED.
    Always call this when changing the state of an expense."""
    fields: dict = {"status": status}
    if risk_level:
        fields["risk_level"] = risk_level
    if notes:
        fields["risk_notes"] = notes
    db.update_expense(expense_id, **fields)
    db.log_audit(expense_id, "risk-evaluator", f"STATUS→{status}",
                 f"risk={risk_level} | {notes}")
    return f"Updated {expense_id}: status={status}" + (f", risk={risk_level}" if risk_level else "")


@tool
def get_expense_details(expense_id: str) -> str:
    """Get full details of an expense record including current status and audit trail."""
    row = db.get_expense(expense_id)
    if not row:
        return f"Expense {expense_id} not found in database."
    audit = db.get_audit_trail(expense_id)
    lines = [
        f"=== {expense_id} ===",
        f"Requester:    {row['requester']}",
        f"Amount:       ${row['amount']:,.2f}",
        f"Department:   {row['department']}",
        f"Type:         {row['expense_type']}",
        f"Description:  {row['description']}",
        f"Vendor:       {row['vendor'] or 'N/A'}",
        f"Status:       {row['status']}",
        f"Risk Level:   {row['risk_level'] or 'N/A'}",
        f"Created:      {row['created_at'][:19]}",
        "",
        "AUDIT TRAIL:",
    ]
    for entry in audit:
        lines.append(f"  [{entry['timestamp'][:19]}] {entry['agent']}: {entry['action']} — {entry['details']}")
    return "\n".join(lines)


@tool
def approve_expense(expense_id: str, approved_by: str = "auto") -> str:
    """Approve an expense and automatically deduct from the department budget.
    Use approved_by='auto' for LOW risk auto-approvals, or the name of the human approver."""
    success = db.approve_expense(expense_id, approved_by=approved_by)
    if success:
        row = db.get_expense(expense_id)
        return (
            f"✅ APPROVED: {expense_id}\n"
            f"   ${row['amount']:,.2f} deducted from {row['department']} budget\n"
            f"   Approved by: {approved_by}"
        )
    return f"❌ Could not approve {expense_id} — record not found."


@tool
def reject_expense(expense_id: str, reason: str, rejected_by: str = "system") -> str:
    """Reject an expense with a reason. No budget deduction occurs."""
    success = db.reject_expense(expense_id, reason=reason, rejected_by=rejected_by)
    if success:
        return f"❌ REJECTED: {expense_id}\n   Reason: {reason}\n   By: {rejected_by}"
    return f"Could not reject {expense_id} — record not found."


@tool
def log_agent_action(expense_id: str, agent: str, action: str, details: str = "") -> str:
    """Log any agent action to the audit trail for compliance and traceability."""
    db.log_audit(expense_id, agent, action, details)
    return f"Logged: [{agent}] {action} for {expense_id}"


@tool
def calculate_risk_level(expense_id: str) -> str:
    """Calculate the risk level for an expense based on amount, policy status, and budget.
    Returns the exact risk level (LOW/MEDIUM/HIGH) and the routing decision to use."""
    row = db.get_expense(expense_id)
    if not row:
        return f"Expense {expense_id} not found."

    amount = row["amount"]
    policy_notes = (row.get("policy_notes") or "").upper()
    budget = db.get_budget(row["department"])
    budget_exceeded = budget and budget["remaining"] < 0

    non_compliant = "NON-COMPLIANT" in policy_notes
    conditional = "CONDITIONAL" in policy_notes

    if amount > 1500 or non_compliant or budget_exceeded:
        risk = "HIGH"
        decision = "CFO-REVIEW"
    elif amount > 500 or conditional:
        risk = "MEDIUM"
        decision = "MANAGER-REVIEW"
    else:
        risk = "LOW"
        decision = "AUTO-APPROVE"

    db.update_expense(expense_id, risk_level=risk)
    db.log_audit(expense_id, "risk-evaluator", "RISK_CALCULATED", f"risk={risk} amount=${amount}")

    return (
        f"Risk Level: {risk}\n"
        f"Decision:   {decision}\n"
        f"Amount:     ${amount:,.2f}\n"
        f"Reason:     {'amount > $1,500' if amount > 1500 else 'amount > $500' if amount > 500 else 'amount ≤ $500'}"
        + (" + NON-COMPLIANT" if non_compliant else "")
        + (" + budget exceeded" if budget_exceeded else "")
    )
