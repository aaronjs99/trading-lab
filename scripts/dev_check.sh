#!/usr/bin/env bash
set -euo pipefail

echo "== trading-lab dev check =="

echo
echo "== Location =="
pwd

echo
echo "== Ensure local data dirs exist =="
mkdir -p data/raw/robinhood data/raw/market data/processed data/reports

echo
echo "== Git status =="
git status --short || {
  echo "ERROR: not a git repo. Run: git init"
  exit 1
}

echo
echo "== Verify data/ is ignored =="
git check-ignore -v data/raw/robinhood || {
  echo "ERROR: data/ is not ignored. Check .gitignore."
  exit 1
}

echo
echo "== Install editable package =="
python -m pip install -e .

echo
echo "== Import check =="
python - <<'PY'
import trading_lab
print("OK:", trading_lab.__file__)
PY

echo
echo "== Tests =="
pytest -q

echo
echo "== Check private data is not tracked =="
if git ls-files | grep -E '^(data/|.*\.csv$|.*\.parquet$|.*\.xlsx$|.*\.png$|.*\.jpg$|.*\.pdf$)'; then
  echo "ERROR: private/generated files may be tracked. Review git ls-files above."
  exit 1
else
  echo "OK: no obvious private/generated files tracked"
fi

echo
echo "== Robinhood CSV presence =="
shopt -s nullglob
csvs=(data/raw/robinhood/*.csv)
if (( ${#csvs[@]} == 0 )); then
  echo "No Robinhood CSVs found yet. Place exports under data/raw/robinhood/"
else
  printf 'Found CSV: %s\n' "${csvs[@]}"
fi

echo
echo "== Done =="
