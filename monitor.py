"""
Budget Monitor — zero LLM calls, zero tokens consumed.

Runs as a background asyncio task alongside the 4 agents.
Every INTERVAL seconds, queries SQLite directly and posts REST alerts
to all rooms the Budget Checker is in whenever a department's remaining
budget drops below LOW_THRESHOLD (20%) or CRITICAL_THRESHOLD (5%).
"""

import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import db
from band.client.rest import AsyncRestClient, ChatMessageRequest, ChatMessageRequestMentionsItem, DEFAULT_REQUEST_OPTIONS

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 30 * 60  # 30 minutes — change to 60 for demo/testing
LOW_THRESHOLD      = 0.20   # 20% remaining → warning
CRITICAL_THRESHOLD = 0.05   # 5%  remaining → critical alert

# Budget Checker identity (used to send messages from)
BUDGET_CHECKER_ID  = os.environ["BAND_BUDGET_CHECKER_ID"]
BUDGET_CHECKER_KEY = os.environ["BAND_BUDGET_CHECKER_KEY"]


def _build_alert(budgets: list[dict]) -> str | None:
    """
    Build an alert message from current budget data.
    Returns None if everything is fine.
    """
    critical = [b for b in budgets if b["remaining"] / b["monthly_limit"] <= CRITICAL_THRESHOLD]
    low      = [b for b in budgets if CRITICAL_THRESHOLD < b["remaining"] / b["monthly_limit"] <= LOW_THRESHOLD]

    if not critical and not low:
        return None

    lines = ["📊 BUDGET MONITOR ALERT", f"Checked at {datetime.now().strftime('%Y-%m-%d %H:%M')}"]

    if critical:
        lines.append("")
        lines.append("🚨 CRITICAL — Near depletion:")
        for b in critical:
            pct = b["remaining"] / b["monthly_limit"] * 100
            lines.append(f"  • {b['department']}: ${b['remaining']:,.0f} left ({pct:.0f}%) — FREEZE non-essential expenses")

    if low:
        lines.append("")
        lines.append("⚠️  WARNING — Budget running low:")
        for b in low:
            pct = b["remaining"] / b["monthly_limit"] * 100
            lines.append(f"  • {b['department']}: ${b['remaining']:,.0f} left ({pct:.0f}%)")

    lines.append("")
    lines.append("No LLM was used to generate this alert.")
    return "\n".join(lines)


async def _get_active_room_ids(client: AsyncRestClient) -> list[str]:
    """Fetch all room IDs the Budget Checker agent is currently in."""
    try:
        resp = await client.agent_api_chats.list_agent_chats(
            request_options=DEFAULT_REQUEST_OPTIONS
        )
        rooms = getattr(resp, "data", []) or []
        return [r.id for r in rooms if hasattr(r, "id")]
    except Exception as e:
        logger.warning("Monitor: could not fetch rooms: %s", e)
        return []


async def _send_to_room(client: AsyncRestClient, room_id: str, text: str) -> None:
    """Send a plain text alert to a Band room."""
    try:
        await client.agent_api_messages.create_agent_chat_message(
            chat_id=room_id,
            message=ChatMessageRequest(
                content=text,
                mentions=[
                    ChatMessageRequestMentionsItem(
                        id=BUDGET_CHECKER_ID,
                        handle="budget-checker",
                        name="Budget Checker",
                    )
                ],
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )
        logger.info("Monitor: alert sent to room %s", room_id)
    except Exception as e:
        logger.warning("Monitor: failed to send to room %s: %s", room_id, e)


async def run_budget_monitor(interval: int = INTERVAL_SECONDS) -> None:
    """
    Background loop — checks budgets every `interval` seconds.
    Uses REST API directly: ZERO LLM calls, ZERO tokens.
    """
    client = AsyncRestClient(api_key=BUDGET_CHECKER_KEY)
    logger.info("Budget Monitor started (interval=%ds, no LLM)", interval)

    while True:
        await asyncio.sleep(interval)

        try:
            budgets = db.get_all_budgets()
            alert = _build_alert(budgets)

            if alert:
                room_ids = await _get_active_room_ids(client)
                for room_id in room_ids:
                    await _send_to_room(client, room_id, alert)
                logger.info("Monitor: alerts sent to %d rooms", len(room_ids))
            else:
                logger.debug("Monitor: all budgets healthy, no alert sent")

        except Exception as e:
            logger.error("Monitor: unexpected error: %s", e, exc_info=True)
