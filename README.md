# trading-lab

`trading-lab` is a local research and decision-support toolkit for studying short-term leveraged ETF trading workflows. The default configuration remains the original TQQQ/QQQ-style setup, but the modeling, dashboard, and backtest paths are intended to follow configured symbols. It combines market-data ingestion, feature generation, regime modeling, walk-forward strategy evaluation, personal trade-history analysis, dashboard reports, plots, and order-reconciliation helpers.

The project is designed as a research lab, not an automated trading bot. It produces probabilities, diagnostics, action cards, allocation suggestions, and risk checks, while deliberately keeping final trading decisions manual. It does not require broker credentials, does not include Robinhood login/API integration, and does not place trades.

## Current status

This repository is at a clean modular baseline:

- Source logic lives under `src/trading_lab/`.
- Scripts in `scripts/` are intentionally thin wrappers.
- Generated/private data is ignored and should not be committed.
- Daily workflow, tests, model diagnostics, plots, and audit tooling are integrated.
- The current default model is explicitly flagged as degraded/weak against a trusted baseline, so the system warns against over-trusting the live signal.

The workflow is intentionally conservative: a model probability alone is not treated as actionable unless model quality, strategy eligibility, trend context, and allocation constraints agree.

## Key capabilities

### Market data pipeline

- Downloads and caches daily market data.
- Skips downloads when local market CSVs were already refreshed that day.
- Builds market features from configured symbols.
- Uses config-backed traded and benchmark symbols rather than hardcoding TQQQ/QQQ throughout the codebase.

Default watchlist includes broad index, leveraged/inverse, sector, and large-cap symbols such as:

- SPY
- QQQ
- TQQQ
- SQQQ
- SMH
- SOXX
- XLK
- AAPL
- MSFT
- NVDA
- AMD
- AVGO
- TSLA
- META
- AMZN
- GOOGL
- PLTR
- HOOD

### Feature generation

The feature builder creates price, trend, volatility, moving-average-distance, drawdown, and prediction-target columns. Prediction targets are represented by config-backed `PredictionTarget` objects.

Current default targets:

- TQQQ hits +5% before -5% within 5 trading days.
- TQQQ hits +8% before -8% within 10 trading days.

These are defaults, not intended as permanent hardcoded assumptions.

### Modeling

The repo includes:

- Regime model training.
- Latest signal scoring.
- Multi-horizon probability scoring.
- Model-zoo evaluation.
- Selected-model scoring.
- Model quality gate.
- Trusted baseline comparison.
- Model degradation diagnostics.

The model quality gate checks whether the selected model is good enough to trust. It currently reports caution when validation metrics are weak.

### Backtesting and strategy selection

The repo supports:

- Daily regime strategy backtests.
- Event strategy backtests.
- Walk-forward strategy optimization.
- Strategy selection with safeguards for infinite or unstable profit-factor values.
- Eligibility checks for live action.

Strategy selection is intentionally conservative and can fall back when strict filters fail, instead of crashing or blindly selecting unstable rows.

### Personal trading analysis

The Robinhood pipeline can ingest exported trade history and generate:

- Normalized trade ledger.
- FIFO realized P&L.
- Positions.
- Symbol/bucket summaries.
- Personal edge summaries.

Private CSVs and generated reports are ignored and should stay local.

### Daily dashboard

The daily workflow generates:

- Full decision summary.
- Concise action card.
- Multi-horizon probabilities.
- Selected prediction model summary.
- Model quality gate.
- Model comparison/degradation report.
- Personal trading edge summary.
- Suggested configured traded-symbol ladder.
- Order reconciliation checks.
- Dashboard plots.

The concise action card is intended for quick daily use.

### Plots

The dashboard generates plots under `data/reports/plots/`, including:

- Configured traded-symbol price context.
- Configured benchmark-symbol regime context.
- Configured traded-symbol drawdown context.
- Model probability history.
- Strategy equity curves.
- Walk-forward top strategies.

Generated plots are local artifacts and are not tracked.

## Repository layout

```text
config/
  account.yaml
  market_symbols.txt
  trading.yaml

scripts/
  Thin command wrappers for workflows and reports.

src/trading_lab/
  backtests/      Backtest engines and walk-forward optimization.
  cli/            Command-center entrypoints.
  config/         Trading symbols, settings, target definitions, column helpers.
  dashboard/      Daily summary and action card generation.
  data/           Market data download/cache utilities.
  devtools/       Audit, cleanup, debug snapshot helpers.
  features/       Market feature and target-column generation.
  models/         Training, model zoo, live scoring, quality, comparison, diagnostics.
  plots/          Dashboard and model plotting.
  reports/        Robinhood/trade-history reports.
  signals/        Allocation, ladder, order parsing/reconciliation, regime signals.
  strategy/       Strategy selection and eligibility.
  workflows/      Orchestration modules.

tests/
  Unit and smoke tests for the modular components.
```

## Quick start

### 1. Clone and enter the repo

```bash
git clone https://github.com/aaronjs99/trading-lab.git
cd trading-lab
```

### 2. Create a Python environment

The project has been developed with Python 3.13 via Miniconda, but any compatible modern Python environment should work if dependencies install cleanly.

```bash
python -m pip install -e .
```

If your environment does not install test/model dependencies automatically, install the expected scientific stack:

```bash
python -m pip install pandas numpy scikit-learn matplotlib yfinance pytest pyyaml
```

### 3. Run the synthetic demo

Fresh public clones can run a no-network demo from committed fake fixtures:

```bash
python -m trading_lab.cli.main demo
# or
./scripts/tl_demo.sh
```

The demo uses tiny synthetic SOXL/XLK/SPY price CSVs from `examples/demo_data/`, writes all generated outputs to a temporary directory, and prints a small action card plus decision readout. It does not touch real `data/`, require Robinhood, or use private files.

### 4. Run tests

```bash
./scripts/tl_test.sh
```

### 5. Run the full daily workflow

```bash
./scripts/tl_full_daily.sh
```

### 6. Show compact status/action card

```bash
./scripts/tl_command.sh card
```

### 7. Show full status

```bash
./scripts/tl_status.sh
```

### 8. Regenerate plots

```bash
python scripts/plot_dashboard.py
python scripts/plot_model_dashboard.py
```

## Common commands

```bash
# No-network synthetic demo
python -m trading_lab.cli.main demo

# Full daily workflow
./scripts/tl_full_daily.sh

# Full saved status
./scripts/tl_status.sh

# Compact action card
./scripts/tl_command.sh card

# Update market data only
python scripts/update_market_data.py

# Build market features only
python scripts/build_market_features.py

# Train regime model
python scripts/train_regime_model.py

# Score latest regime
python scripts/score_latest_regime.py

# Score multi-horizon signals
python scripts/score_multi_horizon.py

# Run model zoo
python scripts/run_model_zoo.py

# Run model quality gate
python scripts/model_quality_gate.py

# Compare current model to trusted baseline
python scripts/model_compare.py

# Generate model degradation diagnostics
python scripts/model_diagnostics.py

# Run repo audit
python scripts/audit_repo.py

# Remove local Python cruft
python scripts/clean_cruft.py
```

## Daily Workflow

The normal daily flow is manual-first and local-only. Use `tlfull` when you want the heavier refresh path that updates market/model reports, then use the lightweight commands for decision review and local portfolio state.

```bash
tlfull
tl decide
tl portfolio status
tl portfolio gui
```

Risk mode changes the portfolio/order advice style without placing orders:

```bash
tl decide --risk-mode conservative
tl decide --risk-mode balanced
tl decide --risk-mode aggressive
```

Local account and portfolio edits update CSV files under `data/raw/portfolio/` only:

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

A typical morning routine:

```bash
tlfull
tl update cash 1000
tl update account-value 5000
tl decide --risk-mode balanced
tl portfolio gui
```

Use the output as decision support only. Review the model quality gate, selected strategy eligibility, current exposure, and open-order checks before making any manual trade. The GUI only reads existing local files and edits local CSVs; it does not connect to a broker, log in to Robinhood, download prices, or place/cancel/modify real orders.

See [docs/local_portfolio.md](docs/local_portfolio.md) for local portfolio CSV schemas, update commands, and risk-mode details.

## Configuration

Main configuration files live in `config/`.

### `config/trading.yaml`

Defines the core trading setup, including:

- core symbol
- benchmark symbol
- traded symbol
- inverse symbol

The default profile is centered on SPY/QQQ/TQQQ/SQQQ and uses the configured default prediction targets. The research profile can be enabled with `TRADING_LAB_PROFILE=research`; it opts into experiment-selected targets when available so research changes can be evaluated without changing the conservative default daily behavior.

### `config/market_symbols.txt`

Defines the market symbols downloaded and used for feature generation.

### `config/account.yaml`

Stores local account assumptions used for allocation/order-reconciliation logic. Do not put sensitive credentials here.

## Generated data and privacy

Generated and private files should stay out of git. The repo is intended to ignore local data such as:

```text
data/
data/raw/
data/processed/
data/reports/
*.csv trade exports
plots
local caches
```

Before pushing publicly, run:

```bash
git ls-files | grep -Ei '(^data/|robinhood|\.csv$|\.xlsx$|\.env|secret|token|password|key|credential)' || true
python scripts/audit_repo.py
```

If anything private appears, remove it from git before publishing.

## Design principles

### Manual-first

This project does not place trades. It produces structured decision support.

### Conservative by default

Weak models should warn, not encourage action. The model quality gate and baseline comparison are part of the decision process.

### Config-driven

Symbols and prediction targets should come from configuration objects, not scattered string literals.

### Modular source, thin scripts

Business logic belongs in `src/trading_lab/`. Scripts should be thin entrypoints.

### Research transparency

The pipeline reports model quality, degradation, diagnostics, strategy selection, and eligibility so that model outputs are auditable.

## Current model caveat

The current generalized feature builder changed the effective training/target window. The repository now correctly reports that the selected model is degraded against the trusted baseline. That is expected and useful: the next research step is to compare target-label semantics and recover model quality while preserving modularity.

Likely next experiments:

- Compare barrier-first-hit targets against horizon-return targets.
- Recover larger usable training windows.
- Improve feature-target alignment.
- Re-evaluate model-zoo metrics.
- Add richer validation dashboards.
- Avoid overfitting to short recent windows.

## License

This project is licensed under the MIT License. See `LICENSE`.

## Disclaimer

This repository is for research, education, and personal decision support only. It is not financial advice, investment advice, or an automated trading system. Leveraged ETFs such as TQQQ and inverse ETFs such as SQQQ involve substantial risk, path dependence, volatility decay, and potential for large drawdowns. Use at your own risk.
