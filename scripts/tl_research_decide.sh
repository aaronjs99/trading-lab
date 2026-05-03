#!/usr/bin/env bash
set -euo pipefail

TRADING_LAB_PROFILE=research PYTHONDONTWRITEBYTECODE=1 python -B -m trading_lab.cli.main decide --profile research "$@"
