"""Generate a synthetic dataset so the app has something to work on from minute one.

Usage: python3 scripts/seed_data.py [--customers 5] [--months 6]
Writes data/accounts.json and data/transactions.json. Deterministic by default.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, timedelta

CATEGORIES = [
    ("groceries", 2000, 45000),
    ("transport", 500, 12000),
    ("restaurants", 1500, 35000),
    ("utilities", 5000, 30000),
    ("healthcare", 3000, 90000),
    ("entertainment", 1000, 25000),
    ("transfer", 5000, 300000),
    ("atm", 10000, 200000),
]
MERCHANTS = {
    "groceries": ["Small Market", "City Grocer", "Corner Shop"],
    "transport": ["Metro Card", "City Taxi", "Fuel Station"],
    "restaurants": ["Coffee House", "Noodle Bar", "Steak Place"],
    "utilities": ["Power Utility", "Water Utility", "Internet Provider"],
    "healthcare": ["Family Clinic", "Pharmacy Chain", "Dental Centre"],
    "entertainment": ["Cinema Hall", "Music Service", "Game Store"],
    "transfer": ["P2P Transfer"],
    "atm": ["ATM Withdrawal"],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--customers", type=int, default=5)
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing data files. Without it, existing files are kept.",
    )
    args = parser.parse_args()

    accounts_path = os.path.join(args.out, "accounts.json")
    transactions_path = os.path.join(args.out, "transactions.json")
    expected = (accounts_path, transactions_path)
    existing = [p for p in expected if os.path.exists(p)]
    if existing and not args.force:
        if len(existing) == len(expected):
            print("Data files already exist, keeping them:")
            for path in existing:
                print(f"  {path}")
            print("Pass --force to regenerate. This guard exists so a readiness check")
            print("can never overwrite the real case dataset.")
            return
        missing = [p for p in expected if p not in existing]
        print("The dataset is incomplete. Present:", file=sys.stderr)
        for path in existing:
            print(f"  {path}", file=sys.stderr)
        print("Missing:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        print(
            "Refusing to mix real and synthetic data. Restore the missing file, "
            "or pass --force to regenerate both.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    rng = random.Random(args.seed)
    os.makedirs(args.out, exist_ok=True)

    accounts: list[dict] = []
    transactions: list[dict] = []
    end = date.today()
    start = end - timedelta(days=30 * args.months)

    for i in range(1, args.customers + 1):
        customer_id = f"CUST-{i:03d}"
        account_id = f"ACC-{i:03d}-1"
        accounts.append(
            {
                "account_id": account_id,
                "customer_id": customer_id,
                "type": "current",
                "currency": "KZT",
                "balance": round(rng.uniform(50_000, 3_000_000), 2),
                "opened_at": (start - timedelta(days=rng.randint(200, 2000))).isoformat(),
            }
        )

        salary_day = rng.randint(1, 28)
        day = start
        tx_index = 0
        while day <= end:
            if day.day == salary_day:
                tx_index += 1
                transactions.append(
                    _tx(customer_id, account_id, day, tx_index, "salary", "Employer Payroll",
                        round(rng.uniform(250_000, 900_000), 2))
                )
            for _ in range(rng.randint(0, 4)):
                category, low, high = rng.choice(CATEGORIES)
                tx_index += 1
                transactions.append(
                    _tx(customer_id, account_id, day, tx_index, category,
                        rng.choice(MERCHANTS[category]), -round(rng.uniform(low, high), 2))
                )
            day += timedelta(days=1)

    _write(accounts_path, accounts)
    _write(transactions_path, transactions)
    print(f"Wrote {len(accounts)} accounts and {len(transactions)} transactions to {args.out}/")


def _tx(customer_id, account_id, day, index, category, merchant, amount) -> dict:
    return {
        "transaction_id": f"TX-{customer_id[-3:]}-{index:05d}",
        "customer_id": customer_id,
        "account_id": account_id,
        "date": day.isoformat(),
        "amount": amount,
        "currency": "KZT",
        "category": category,
        "merchant": merchant,
        "channel": "card" if amount < 0 else "transfer",
    }


def _write(path: str, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
