# Nectar Capital — Investor Data Room

Live data room for investor reporting. Hosted on GitHub Pages.

## Project Structure

```
nectar-data-room/
├── index.html              ← Main app (loads data from JSON at runtime)
├── data/
│   ├── deals.json          ← Deal data (source of truth — updated monthly)
│   ├── memos.json          ← Investment memo details per deal
│   └── photos.json         ← Property photo path mappings
├── images/                 ← Property photos ({deal_id}.png)
├── scripts/
│   ├── update_payments.py  ← Monthly payment update script
│   └── logs/               ← Auto-generated update logs
└── README.md
```

## Monthly Payment Update (2 minutes)

### 1. Export the payment split CSV from LoanPro

### 2. Run the update script

```bash
# Preview changes first (no files modified)
python scripts/update_payments.py Payment_Split_April.csv --dry-run

# Apply changes
python scripts/update_payments.py Payment_Split_April.csv

# See every deal updated
python scripts/update_payments.py Payment_Split_April.csv --verbose
```

### 3. Push to GitHub Pages

```bash
git add data/deals.json
git commit -m "April 2026 payment update"
git push
```

That's it. No editing HTML, no touching code.

## What the Script Does

1. Reads the CSV and aggregates `Split Amount` by `LoanPro ID`
2. Loads `data/deals.json`
3. Adds the total collected per deal to the `collected` field
4. Saves the updated JSON
5. Creates a timestamped log in `scripts/logs/`

If a LoanPro ID from the CSV doesn't match any deal in `deals.json`, it gets flagged in the summary (e.g., new deals not yet added to the data room).

## Adding a New Deal

Edit `data/deals.json` and add an entry:

```json
{
  "id": "1285",
  "name": "New Property LLC",
  "asset": "Multifamily",
  "type": "Preferred Equity",
  "vintage": 2026,
  "advance": 500000.0,
  "collected": 0,
  "outstanding": 500000.0,
  "monthlyPmt": 10000.0,
  "irr": 22.0,
  "ltv": 65.0,
  "dscr": 1.25,
  "status": "Open",
  "term": 60,
  "fundDate": "2026-04"
}
```

Optionally add a memo in `data/memos.json` and a photo in `images/`.

## Local Development

Needs to be served over HTTP (not `file://`) for JSON fetch to work:

```bash
# Python
python -m http.server 8000

# Node
npx serve .
```

Then open `http://localhost:8000`
