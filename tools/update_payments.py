#!/usr/bin/env python3
"""
Nectar Data Room — Payment Update Tool

Usage:
    python update_payments.py <payment_csv> [--data path/to/deals.json] [--dry-run]

Examples:
    python update_payments.py Payment_Split_March.csv
    python update_payments.py Payment_Split_March.csv --dry-run
    python update_payments.py Payment_Split_March.csv --data ../data/deals.json
"""

import csv
import json
import argparse
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def parse_amount(raw: str) -> float:
    """Parse a currency string like '$13,305.63' into a float."""
    cleaned = raw.strip().replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def load_csv_payments(csv_path: str) -> dict[str, float]:
    """Read a Payment Split CSV and aggregate Split Amount by LoanPro ID."""
    totals: dict[str, float] = defaultdict(float)
    row_count = 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lid = row["LoanPro ID"].strip()
            amt = parse_amount(row["Split Amount"])
            totals[lid] += amt
            row_count += 1

    return dict(totals), row_count


def update_deals(data: dict, payments: dict[str, float]) -> list[dict]:
    """Apply payment totals to deals. Returns a log of changes."""
    deal_ids = {d["id"] for d in data["deals"]}
    changes = []

    for deal in data["deals"]:
        if deal["id"] in payments:
            old = deal["collected"]
            march_amt = payments[deal["id"]]
            deal["collected"] = round(old + march_amt, 2)
            changes.append({
                "id": deal["id"],
                "name": deal["name"],
                "old_collected": old,
                "payment": march_amt,
                "new_collected": deal["collected"],
            })

    # Flag CSV IDs with no matching deal
    missing = set(payments.keys()) - deal_ids
    return changes, missing


def main():
    parser = argparse.ArgumentParser(
        description="Update deals.json with a new Payment Split CSV"
    )
    parser.add_argument("csv_file", help="Path to the Payment Split CSV")
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent.parent / "data" / "deals.json"),
        help="Path to deals.json (default: ../data/deals.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to file",
    )
    args = parser.parse_args()

    # ── Load data ──
    print(f"\n  Loading deals from: {args.data}")
    with open(args.data, "r") as f:
        data = json.load(f)
    print(f"  Found {len(data['deals'])} deals (last updated: {data.get('lastUpdated', '?')})")

    # ── Parse CSV ──
    print(f"  Parsing CSV: {args.csv_file}")
    payments, row_count = load_csv_payments(args.csv_file)
    total_collected = sum(payments.values())
    print(f"  {row_count} rows → {len(payments)} unique LoanPro IDs → ${total_collected:,.2f} total\n")

    # ── Apply updates ──
    changes, missing = update_deals(data, payments)

    # ── Report ──
    print(f"  {'─' * 72}")
    print(f"  {'ID':<8} {'Deal Name':<40} {'Before':>12} {'+ Payment':>12} {'= After':>12}")
    print(f"  {'─' * 72}")
    for c in sorted(changes, key=lambda x: -x["payment"]):
        print(
            f"  {c['id']:<8} {c['name'][:38]:<40} "
            f"${c['old_collected']:>10,.2f} "
            f"${c['payment']:>10,.2f} "
            f"${c['new_collected']:>10,.2f}"
        )
    print(f"  {'─' * 72}")
    print(f"  {len(changes)} deals updated  |  ${sum(c['payment'] for c in changes):,.2f} applied\n")

    if missing:
        print(f"  ⚠  {len(missing)} CSV IDs not found in deals.json: {sorted(missing, key=int)}")
        print(f"     These may need to be added as new deals.\n")

    # ── Write ──
    if args.dry_run:
        print("  🔍 DRY RUN — no changes written.\n")
    else:
        data["lastUpdated"] = date.today().isoformat()
        with open(args.data, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  ✓ deals.json updated (lastUpdated → {data['lastUpdated']})")
        print(f"  Next: git add . && git commit -m \"Payment update\" && git push\n")


if __name__ == "__main__":
    main()
