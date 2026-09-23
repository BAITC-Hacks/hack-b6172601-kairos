"""In-memory dataset loaded from data/*.json.

Swap this for the real data source when the case is published. The interface is
small on purpose: three methods, all pure.
"""
from __future__ import annotations

import json
import os
from datetime import date
from functools import lru_cache
from typing import Any

DATA_DIR = os.getenv("DATA_DIR", "data")


class Store:
    def __init__(self, accounts: list[dict], transactions: list[dict]) -> None:
        self._accounts = accounts
        self._transactions = transactions

    def accounts_for(self, customer_id: str) -> list[dict[str, Any]]:
        # Copies, not the stored objects: the store is cached process-wide, so
        # a tool that mutates a returned row would corrupt it for every later
        # request. Cheap here, and it removes a whole class of bug.
        return [dict(a) for a in self._accounts if a["customer_id"] == customer_id]

    def search_transactions(
        self,
        customer_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        category: str | None = None,
        min_amount: float | None = None,
    ) -> list[dict[str, Any]]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must not be later than date_to.")

        rows = [t for t in self._transactions if t["customer_id"] == customer_id]
        if date_from:
            rows = [t for t in rows if date.fromisoformat(t["date"]) >= date_from]
        if date_to:
            rows = [t for t in rows if date.fromisoformat(t["date"]) <= date_to]
        if category:
            rows = [t for t in rows if t["category"].lower() == category.lower()]
        if min_amount is not None:
            rows = [t for t in rows if abs(t["amount"]) >= min_amount]
        return [dict(t) for t in sorted(rows, key=lambda t: t["date"], reverse=True)]

    def spending_by_category(
        self,
        customer_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.search_transactions(customer_id, date_from=date_from, date_to=date_to)
        totals: dict[str, float] = {}
        for row in rows:
            if row["amount"] >= 0:
                continue  # income, not spending
            totals[row["category"]] = totals.get(row["category"], 0.0) + abs(row["amount"])
        return [
            {"category": k, "total": round(v, 2)}
            for k, v in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
        ]


@lru_cache
def get_store() -> Store:
    accounts = _load("accounts.json")
    transactions = _load("transactions.json")
    return Store(accounts=accounts, transactions=transactions)


def _load(filename: str) -> list[dict]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
