# Portfolio GUI

`tl portfolio gui` starts a small local browser dashboard for reviewing the daily decision, local portfolio CSVs, manually tracked open orders, snapshots, and decision outcomes.

The GUI is local decision support only:

- It binds to `127.0.0.1`.
- It uses Python standard-library `http.server`.
- It reads existing local files and reports.
- It edits local CSV files only.
- It does not log in to Robinhood.
- It does not use a broker API.
- It does not place, cancel, or modify real orders.
- It does not run `tlfull`, train models, run backtests, generate plots, or download prices from dashboard refresh.

Do not share screenshots of your real dashboard if they contain account values, positions, notes, or order details. The examples below are synthetic text mockups only.

## Launch

```bash
tl portfolio gui
```

The command prints a local URL like:

```text
Local-only portfolio GUI: http://127.0.0.1:8765/
```

Open that URL in a browser on the same machine. The server is intended for local use only.

## Top Controls

The top of the dashboard has the title, tabs, and global status controls.

Synthetic example:

```text
Trading Lab
Local decision dashboard. No broker connection.

[ Daily ] [ Positions ] [ Open orders ] [ Edit local CSVs ]

Risk mode: [ Conservative ] [ Balanced ] [ Aggressive ]
Local time: 2026-05-04 09:31:22
Last local refresh: 2026-05-04 09:31:22
Report updated: 2026-05-04 09:10
Account value: $5,000.00
Cash: $1,000.00
```

Risk mode is dashboard-wide. Changing it reloads the local page with the selected mode in the URL, for example:

```text
http://127.0.0.1:8765/?tab=daily&risk_mode=balanced
```

Risk modes:

- `conservative`: exposure-first.
- `balanced`: exposure plus ladder/order quality.
- `aggressive`: trend/risk-seeking while still showing exposure warnings.

## Daily Tab

The Daily tab is the main morning review screen. It shows:

- The current action.
- The decision sentence.
- Current traded-symbol position and allocation.
- Pending buy/sell notional.
- Max recommended exposure and buy capacity.
- Portfolio action.
- Advice and interpretation.
- Suggested order ideas.
- Portfolio summary.
- Dates and update metadata.
- Snapshot controls.
- Outcome tracking controls.

Synthetic example:

```text
Daily decision

HOLD
Now: hold existing TQQQ position.
Decision: HOLD TQQQ; no fresh signal to increase risk.

Traded symbol: TQQQ
Current position: 4
Current allocation: 4.8%
Pending buys: $580.00
Pending sells: $274.00
Max exposure: $250.00
Buy capacity: $0.00
Portfolio action: cancel/reduce orders
Risk mode: balanced
```

The dashboard refreshes itself hourly from existing local files. This refresh only rereads local CSVs and reports. Run `tlfull` when you want to update market data, features, model reports, plots, and the daily decision summary.

## Positions Tab

The Positions tab combines the local positions table with sizing and trend review fields.

Columns include:

- Symbol
- Quantity
- Price
- Value
- Allocation
- Updated
- Review status
- Review note
- Price date
- Trend status
- Trend note

Synthetic example:

```text
Symbol  Quantity  Price    Value   Allocation  Review status  Trend status
TQQQ    4         $60.00   $240.00 4.8%        TRADED_SYMBOL  REVIEW
META    0.04      $600.00  $24.00  0.5%        OK_SMALL       UPTREND
```

Non-traded holdings get simple local trend/status indicators from local market CSVs only. The GUI does not claim model-backed buy/sell predictions for non-traded holdings.

## Open Orders Tab

The Open orders tab combines manually tracked local open orders with recommendation fields.

Columns include:

- Recommendation
- Symbol
- Side
- Type
- Quantity
- Limit
- Notional
- Status
- Submitted
- Price relation
- Ladder relation
- Projected exposure
- Reason

Synthetic example:

```text
Recommendation  Symbol  Side  Qty  Limit   Notional  Reason
REVIEW          TQQQ    buy   10   $58.00  $580.00   Deep order; exposure warning remains.
KEEP            TQQQ    sell  4    $68.50  $274.00   Sell order reduces overexposure.
```

Recommendations are local advice only. They do not place, cancel, or modify broker orders.

## Edit Local CSVs Tab

The Edit local CSVs tab contains forms for:

- Saving cash/account value.
- Setting a position quantity.
- Applying a buy/sell position update.
- Adding a manually tracked buy/sell limit order.
- Clearing orders for one symbol.
- Clearing all local open orders.

The warning in this tab is literal:

```text
Local CSV update only. This does not place, cancel, or modify broker orders.
```

CSV edits are written under `data/raw/portfolio/`, which is gitignored.

## Snapshots Card

The Daily tab includes a Portfolio snapshots card.

Use it to record a point-in-time local portfolio snapshot for future review:

```text
Portfolio snapshots
[ Notes __________________ ] [ Record snapshot ]

Recent snapshots
Timestamp            Mode      Action  Traded  Value    Notes
2026-05-04T09:30:00 balanced  HOLD    TQQQ    $240.00  morning review
```

Snapshots are written to:

```text
data/processed/portfolio/snapshots.csv
```

That file is local and gitignored.

## Outcome Tracking Card

The Daily tab also includes a Decision outcomes card.

Use it to record the current decision/order-advice state and later update future returns from local market CSVs:

```text
Decision outcomes
[ Notes __________________ ] [ Record outcome ]
[ Update outcomes ]

Recent outcomes
Timestamp            Mode      Action  Symbol  Price    5d return  Status
2026-05-04T09:30:00 balanced  HOLD    TQQQ    $60.00   5.0%       UPDATED
```

Outcomes are written to:

```text
data/processed/portfolio/decision_outcomes.csv
```

That file is local and gitignored. Updating outcomes does not download prices; it only fills future prices/returns when enough later rows already exist in local market CSVs.

## When To Run `tlfull`

Run `tlfull` when you want fresh market/model/report artifacts:

```bash
tlfull
tl decide --risk-mode balanced
tl portfolio gui
```

Use the GUI between heavy refreshes for local review and local CSV edits. GUI refresh, tab switching, snapshot recording, and outcome updating stay lightweight.

## Privacy Checklist

Before committing documentation or examples:

- Do not add real screenshots with account values or positions.
- Do not add `data/`, `reports/`, `plots/`, or CSV exports.
- Use synthetic/redacted examples only.
- Run `python -B scripts/audit_repo.py`.
