#!/usr/bin/env bash
set -euo pipefail

clear

echo "== trading-lab reset =="
echo

echo "== Location =="
pwd

echo
echo "== Git status =="
git status --short

echo
echo "== Ensure local ignored data dirs exist =="
mkdir -p data/raw/robinhood data/raw/market data/processed data/reports

echo
echo "== Verify data/ is ignored =="
git check-ignore -v data/raw/robinhood || {
  echo "ERROR: data/ is not ignored"
  exit 1
}

echo
echo "== Tests =="
python -m pytest

echo
echo "== Done =="
