# trading-lab

Python research repo for reconstructing Robinhood trading history, analyzing realized P&L and behavioral edge, and backtesting a long-biased TQQQ/SPY ladder strategy.

This repo is intentionally research-only. It does not include live trading or broker API order placement.

## Privacy Rules

The entire `data/` folder is gitignored. Do not commit raw CSVs, processed ledgers, reports, plots, brokerage data, or private financial data.

Tracked files should stay limited to code, tests, configs, docs, and safe examples.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Create local data folders:

```powershell
New-Item -ItemType Directory -Force data\raw\robinhood, data\processed, data\reports
```

Export your Robinhood CSVs locally and place them under:

```text
data/raw/robinhood/
```

The loader is flexible: it inspects CSV columns and normalizes common fields such as symbol, side, quantity, price, amount, fees, and executed timestamp.

## Scripts

Ingest Robinhood CSVs and build normalized trade, realized P&L, and position files:

```powershell
python scripts/ingest_robinhood.py --input data/raw/robinhood --output data/processed
```

Download market data:

```powershell
python scripts/download_market_data.py --symbols SPY TQQQ --start 2018-01-01 --output data/processed/market_data.csv
```

Run edge summary report:

```powershell
python scripts/run_edge_report.py --trades data/processed/normalized_trades.csv --output data/reports
```

Run TQQQ/SPY ladder backtest skeleton:

```powershell
python scripts/run_tqqq_backtest.py --market-data data/processed/market_data.csv --output data/reports
```

## Tests

```powershell
pytest
```

## Current Scope

- Flexible Robinhood CSV ingestion
- FIFO realized P&L
- Position reconstruction
- Basic summary report by symbol
- Simple long-biased TQQQ ladder backtest skeleton

## Not Included

- Live trading
- Broker API order placement
- Private financial data
- Generated reports or plots in git
