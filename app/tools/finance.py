"""Example tools over the local dataset.

REPLACE THESE with tools for the actual case. They exist so the agent loop is
already wired end to end and the first real tool is a copy-paste away.
"""
from __future__ import annotations

from datetime import date

from app.agent.registry import tool
from app.data.store import get_store


@tool(
    name="list_accounts",
    description="List the accounts of a customer with their currency and current balance.",
    parameters={
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer identifier, e.g. CUST-001"},
        },
        "required": ["customer_id"],
    },
)
def list_accounts(customer_id: str) -> dict:
    store = get_store()
    accounts = store.accounts_for(customer_id)
    if not accounts:
        return {"error": f"No accounts found for customer {customer_id}."}
    return {"customer_id": customer_id, "accounts": accounts}


@tool(
    name="search_transactions",
    description=(
        "Search transactions of a customer. Filter by date range, merchant category "
        "or minimum amount. Returns at most 50 rows, newest first."
    ),
    parameters={
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "date_from": {"type": "string", "description": "ISO date, inclusive, e.g. 2026-08-01"},
            "date_to": {"type": "string", "description": "ISO date, inclusive"},
            "category": {"type": "string", "description": "Merchant category, e.g. groceries"},
            "min_amount": {"type": "number", "description": "Minimum absolute amount"},
        },
        "required": ["customer_id"],
    },
)
def search_transactions(
    customer_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    min_amount: float | None = None,
) -> dict:
    store = get_store()
    try:
        rows = store.search_transactions(
            customer_id=customer_id,
            date_from=_parse_date(date_from),
            date_to=_parse_date(date_to),
            category=category,
            min_amount=min_amount,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    return {"count": len(rows), "transactions": rows[:50]}


@tool(
    name="spending_summary",
    description="Aggregate a customer's spending by merchant category over a date range.",
    parameters={
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "date_from": {"type": "string"},
            "date_to": {"type": "string"},
        },
        "required": ["customer_id"],
    },
)
def spending_summary(customer_id: str, date_from: str | None = None, date_to: str | None = None) -> dict:
    store = get_store()
    try:
        summary = store.spending_by_category(
            customer_id=customer_id,
            date_from=_parse_date(date_from),
            date_to=_parse_date(date_to),
        )
    except ValueError as exc:
        return {"error": str(exc)}
    if not summary:
        return {"error": f"No spending found for customer {customer_id} in that period."}
    return {"customer_id": customer_id, "by_category": summary}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date: {value!r}. Use ISO format YYYY-MM-DD.") from exc
