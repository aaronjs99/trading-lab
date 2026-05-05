# Local Portfolio Workflow

`trading-lab` can read a small local portfolio snapshot so `tl decide`, `tl portfolio status`, and `tl portfolio gui` can account for current holdings, saved cash/account value, and manually tracked open orders.

This is local decision support only:

- `data/` is gitignored and should not be committed.
- There is no broker connection.
- There is no Robinhood login or broker API.
- There is no automated order placement.
- The browser GUI only edits local CSV files.
- Market prices are read from local market CSVs under `data/raw/market/`; prices are not stored in `positions.csv`.

## Daily Workflow

Use `tlfull` for the heavy refresh path. It updates market data, features, models/reports, plots, and daily summaries. Use the other commands for lightweight review and local CSV edits.

```bash
tlfull
tl decide
tl portfolio status
tl portfolio gui
```

Decision review supports risk modes:

```bash
tl decide --risk-mode conservative
tl decide --risk-mode balanced
tl decide --risk-mode aggressive
```

Record local snapshots for later outcome analysis:

```bash
tl portfolio snapshot --risk-mode balanced --notes "morning review"
tl portfolio snapshots
tl decide --risk-mode balanced --snapshot --snapshot-notes "after review"
tl portfolio outcome-record --risk-mode balanced --notes "track decision"
tl portfolio outcome-update
tl portfolio outcomes
tl decide --risk-mode balanced --record-outcome --outcome-notes "track decision"
```

Local portfolio updates:

```bash
tl update cash AMOUNT
tl update account-value AMOUNT
tl update buy SYMBOL QTY
tl update sell SYMBOL QTY
tl update set SYMBOL QTY
tl update order buy SYMBOL QTY LIMIT
tl update order sell SYMBOL QTY LIMIT
tl update order clear SYMBOL
tl update order clear-all
```

Typical morning routine:

```bash
tlfull
tl update cash 1000
tl update account-value 5000
tl decide --risk-mode balanced
tl portfolio snapshot --risk-mode balanced --notes "morning review"
tl portfolio outcome-record --risk-mode balanced --notes "morning review"
tl portfolio gui
```

## CSV Schemas

Create these files only if you want local portfolio-aware decisions. Missing files are allowed and produce an empty local portfolio state.

### `data/raw/portfolio/positions.csv`

Columns:

```text
symbol,quantity,notes,updated_at
```

Example:

```csv
symbol,quantity,notes,updated_at
TQQQ,4,current_position,2026-05-04
META,0.040567,current_position,2026-05-04
```

Do not store prices here. Position values are calculated from the latest local market CSV close/adjusted close.

### `data/raw/portfolio/open_orders.csv`

Columns:

```text
symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes
```

Example:

```csv
symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes
TQQQ,buy,limit,10,58.00,GTC,placed,2026-04-29,current_open_order
TQQQ,sell,limit,4,68.50,GTC,placed,2026-04-29,current_open_order
```

These are manually tracked local orders. They are not read from a broker, and changing them does not place, cancel, or modify broker orders.

### `data/raw/portfolio/account.csv`

Columns:

```text
key,value,updated_at
```

Example:

```csv
key,value,updated_at
cash,1000,2026-05-04
account_value,5000,2026-05-04
```

CLI flags can override saved account values for a single decision run:

```bash
tl decide --account-value 5000 --cash 1000
```

## Risk Modes

- `conservative`: exposure-first. If current plus pending exposure exceeds the recommended max, buy orders are likely to be cancel/reduce candidates.
- `balanced`: exposure plus ladder quality. It keeps exposure warnings, but deep or better-quality ladder orders may be reviewed instead of automatically canceled.
- `aggressive`: trend/risk-seeking. It can tolerate higher drawdown risk and rank orders by trend and ladder quality, while still showing exposure warnings.

Risk mode changes local advice only. It does not trigger downloads, broker actions, or automated trading.

## Snapshot History

Portfolio snapshots are optional local history rows for future plots and outcome tracking. They read the current local portfolio files, existing market CSVs, and existing reports, then append one row to:

```text
data/processed/portfolio/snapshots.csv
```

That file lives under gitignored `data/`, so it is private local state and should not be committed. Snapshot commands are lightweight: they do not run `tlfull`, download market data, train models, run backtests, generate plots, connect to a broker, or place/cancel orders.

Use:

```bash
tl portfolio snapshot --risk-mode balanced --notes "manual review"
tl portfolio snapshots --limit 10
```

`tl decide` does not write snapshots by default, but you can opt in for a single run:

```bash
tl decide --risk-mode balanced --snapshot --snapshot-notes "decision recorded"
```

## Outcome Tracking

Decision outcome tracking is optional local history for evaluating whether daily decisions and suggested order ideas were useful. It appends rows to:

```text
data/processed/portfolio/decision_outcomes.csv
```

That file is under gitignored `data/` and should stay private/local. Outcome commands only read existing reports, local portfolio CSVs, and local market CSVs. They do not run `tlfull`, download prices, train models, run backtests, generate plots, connect to a broker, or place/cancel orders.

Record the current decision state:

```bash
tl portfolio outcome-record --risk-mode balanced --notes "morning decision"
```

Update previously recorded rows after enough local future market data exists:

```bash
tl portfolio outcome-update
```

View recent rows:

```bash
tl portfolio outcomes --limit 10
```

Optional aliases are also available:

```bash
tl outcome record --risk-mode balanced --notes "morning decision"
tl outcome update
tl outcome list
```

`tl decide` does not record outcomes by default, but you can opt in for a single run:

```bash
tl decide --risk-mode balanced --record-outcome --outcome-notes "decision tracked"
```

Future outcome fields are filled only from local market CSVs when enough later rows exist. Until then, rows remain `PENDING` or `INSUFFICIENT_FUTURE_DATA`; missing local price data is marked `PRICE_MISSING`.

## GUI

Start the local dashboard:

```bash
tl portfolio gui
```

The GUI binds to localhost only and uses existing local files. It can edit `positions.csv`, `open_orders.csv`, and `account.csv` through forms, then reload the dashboard. It does not run the full daily workflow, download market data, train models, generate plots, or connect to any broker.
