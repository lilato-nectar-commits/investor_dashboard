#!/usr/bin/env python3
"""
Nectar Data Room — Payment Update Script
=========================================
Processes a LoanPro payment split CSV and updates deals.json with new collections.

Usage:
    python update_payments.py <payment_csv>
    python update_payments.py Payment_Split_March.csv
    python update_payments.py Payment_Split_March.csv --dry-run

What it does:
    1. Reads the payment CSV and aggregates Split Amount by LoanPro ID
    2. Loads deals.json
    3. Adds March collections to each matching deal's "collected" field
    4. Writes updated deals.json
    5. Prints a summary report

Flags:
    --dry-run    Show what would change without writing to disk
    --verbose    Print every deal update line
"""

import csv
import json
import sys
import os
from collections import defaultdict
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(SCRIPT_DIR, '..', 'data')
DEALS_FILE  = os.path.join(DATA_DIR, 'deals.json')
LOG_DIR     = os.path.join(SCRIPT_DIR, 'logs')


def parse_amount(raw: str) -> float:
    """Parse dollar amounts like '$1,234.56' or '-$500' into float."""
    cleaned = raw.strip().replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def aggregate_csv(csv_path: str) -> dict:
    """Read payment CSV, return {loanpro_id: total_split_amount}."""
    totals = defaultdict(float)
    row_count = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        # Validate expected columns exist
        required = {'LoanPro ID', 'Split Amount'}
        if not required.issubset(set(reader.fieldnames or [])):
            missing = required - set(reader.fieldnames or [])
            print(f"  ERROR: CSV missing required columns: {missing}")
            print(f"  Found columns: {reader.fieldnames}")
            sys.exit(1)

        for row in reader:
            lid = row['LoanPro ID'].strip()
            if not lid:
                continue
            amt = parse_amount(row['Split Amount'])
            totals[lid] += amt
            row_count += 1

    return dict(totals), row_count


def load_deals() -> list:
    """Load deals.json."""
    if not os.path.exists(DEALS_FILE):
        print(f"  ERROR: {DEALS_FILE} not found")
        sys.exit(1)
    with open(DEALS_FILE, 'r') as f:
        return json.load(f)


def save_deals(deals: list):
    """Write deals.json with consistent formatting."""
    with open(DEALS_FILE, 'w') as f:
        json.dump(deals, f, indent=2)


def save_log(csv_name: str, updates: list, unmatched: dict):
    """Save a timestamped log of what was updated."""
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(LOG_DIR, f'{ts}_{os.path.basename(csv_name)}.log')

    with open(log_path, 'w') as f:
        f.write(f"Payment Update Log — {datetime.now().isoformat()}\n")
        f.write(f"Source: {csv_name}\n")
        f.write(f"{'='*70}\n\n")

        f.write(f"UPDATED DEALS ({len(updates)})\n")
        f.write(f"{'-'*70}\n")
        for u in updates:
            f.write(f"  {u['id']:>6}  {u['name']:<45} "
                    f"${u['old']:>12,.2f} + ${u['added']:>10,.2f} = ${u['new']:>12,.2f}\n")

        if unmatched:
            f.write(f"\nUNMATCHED IDS ({len(unmatched)})\n")
            f.write(f"{'-'*70}\n")
            for lid, amt in sorted(unmatched.items(), key=lambda x: int(x[0])):
                f.write(f"  {lid:>6}  ${amt:>12,.2f}  (no matching deal in deals.json)\n")

        total_added = sum(u['added'] for u in updates)
        f.write(f"\nTOTAL ADDED: ${total_added:,.2f}\n")

    return log_path


def main():
    # ── Parse args ──
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    verbose = '--verbose' in args
    csv_files = [a for a in args if not a.startswith('--')]

    if not csv_files:
        print("Usage: python update_payments.py <payment_csv> [--dry-run] [--verbose]")
        sys.exit(1)

    csv_path = csv_files[0]
    if not os.path.exists(csv_path):
        print(f"  ERROR: File not found: {csv_path}")
        sys.exit(1)

    # ── Process ──
    print(f"\n{'='*60}")
    print(f"  NECTAR PAYMENT UPDATE")
    print(f"{'='*60}")
    print(f"  Source:   {os.path.basename(csv_path)}")
    print(f"  Mode:     {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    # Step 1: Aggregate CSV
    print("  [1/3] Parsing CSV...")
    totals, row_count = aggregate_csv(csv_path)
    print(f"         {row_count} rows → {len(totals)} unique LoanPro IDs")
    print(f"         Grand total: ${sum(totals.values()):,.2f}")

    # Step 2: Load deals
    print("  [2/3] Loading deals.json...")
    deals = load_deals()
    deal_map = {d['id']: d for d in deals}
    print(f"         {len(deals)} deals loaded")

    # Step 3: Apply updates
    print("  [3/3] Applying updates...")
    updates = []
    unmatched = {}
    matched_ids = set()

    for lid, march_amt in sorted(totals.items(), key=lambda x: int(x[0])):
        if lid in deal_map:
            deal = deal_map[lid]
            old_collected = deal['collected']
            new_collected = round(old_collected + march_amt, 2)
            deal['collected'] = new_collected
            matched_ids.add(lid)

            update_info = {
                'id': lid,
                'name': deal['name'],
                'old': old_collected,
                'added': march_amt,
                'new': new_collected
            }
            updates.append(update_info)

            if verbose:
                print(f"         {lid} {deal['name'][:35]:<35} "
                      f"+${march_amt:>10,.2f} → ${new_collected:>12,.2f}")
        else:
            unmatched[lid] = march_amt

    # ── Summary ──
    print()
    print(f"  {'─'*56}")
    print(f"  Deals updated:     {len(updates)}")
    print(f"  Total added:       ${sum(u['added'] for u in updates):,.2f}")
    if unmatched:
        print(f"  Unmatched IDs:     {len(unmatched)} (${sum(unmatched.values()):,.2f})")
        for lid, amt in sorted(unmatched.items(), key=lambda x: int(x[0])):
            print(f"    → {lid}: ${amt:,.2f}")
    print(f"  {'─'*56}")

    # ── Write ──
    if dry_run:
        print("\n  DRY RUN — no files modified.\n")
    else:
        save_deals(deals)
        log_path = save_log(csv_path, updates, unmatched)
        print(f"\n  ✓ deals.json updated")
        print(f"  ✓ Log saved: {os.path.basename(log_path)}")
        print()


if __name__ == '__main__':
    main()
