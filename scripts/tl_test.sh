#!/usr/bin/env bash
set -euo pipefail

PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider "$@"
find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name "*.egg-info" \) -prune -exec rm -rf {} +
