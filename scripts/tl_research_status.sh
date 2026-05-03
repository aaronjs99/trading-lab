#!/usr/bin/env bash
set -euo pipefail
TRADING_LAB_PROFILE=research python -m trading_lab.cli.status "$@"
