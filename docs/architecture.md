# Architecture

`trading-lab` is organized around thin command wrappers and modular source packages.

## Package layout

```text
src/trading_lab/
  backtests/   Backtest engines and walk-forward optimization.
  cli/         Command center entrypoints.
  config/      Trading settings, symbols, column helpers, prediction targets.
  dashboard/   Daily decision summary and compact action card.
  data/        Market data download/cache utilities.
  devtools/    Audit, cleanup, and debug snapshot utilities.
  features/    Market feature and prediction target generation.
  models/      Training, scoring, model zoo, quality, comparison, diagnostics.
  plots/       Dashboard/model plotting.
  reports/     Trade-history and bucket reports.
  signals/     Allocation, ladders, orders, regime signals.
  strategy/    Strategy selection and live eligibility checks.
  workflows/   Multi-step workflow orchestration.
```

## Data flow

```text
market CSVs
  -> feature builder
  -> regime model training
  -> latest signal and multi-horizon scoring
  -> walk-forward strategy optimization
  -> model zoo and quality gate
  -> daily summary, action card, plots, and order checks
```

## Privacy boundary

The repository should not track:

- `data/`
- Robinhood CSV exports
- generated reports
- generated plots
- credentials
- account-specific private data

Use:

```bash
python scripts/audit_repo.py
```

## Design rules

- Prefer config-driven symbols and targets.
- Avoid hardcoded TQQQ/QQQ assumptions outside defaults/config.
- Keep workflows reproducible.
- Keep scripts thin.
- Make weak model quality explicit in dashboard output.
