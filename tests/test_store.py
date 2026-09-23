"""Tests for the dataset layer. Pure functions, no network."""
from datetime import date

import pytest

from app.data.store import Store

ACCOUNTS = [{"account_id": "ACC-1", "customer_id": "CUST-001", "currency": "KZT", "balance": 100.0}]
TRANSACTIONS = [
    {"customer_id": "CUST-001", "date": "2026-08-01", "amount": -1000.0, "category": "groceries"},
    {"customer_id": "CUST-001", "date": "2026-08-05", "amount": -500.0, "category": "transport"},
    {"customer_id": "CUST-001", "date": "2026-08-10", "amount": 200000.0, "category": "salary"},
    {"customer_id": "CUST-002", "date": "2026-08-10", "amount": -700.0, "category": "groceries"},
]


@pytest.fixture
def store() -> Store:
    return Store(accounts=ACCOUNTS, transactions=TRANSACTIONS)


def test_accounts_are_scoped_to_the_customer(store):
    assert len(store.accounts_for("CUST-001")) == 1
    assert store.accounts_for("CUST-999") == []


def test_date_range_filter(store):
    rows = store.search_transactions("CUST-001", date_from=date(2026, 8, 2), date_to=date(2026, 8, 6))
    assert len(rows) == 1
    assert rows[0]["category"] == "transport"


def test_inverted_date_range_is_rejected(store):
    with pytest.raises(ValueError):
        store.search_transactions("CUST-001", date_from=date(2026, 8, 10), date_to=date(2026, 8, 1))


def test_spending_summary_excludes_income(store):
    summary = store.spending_by_category("CUST-001")
    categories = [row["category"] for row in summary]
    assert "salary" not in categories
    assert summary[0] == {"category": "groceries", "total": 1000.0}
