# Contributing

This repository is a personal research and decision-support lab. Contributions should preserve the current design principles:

- Keep business logic in `src/trading_lab/`.
- Keep scripts in `scripts/` as thin wrappers.
- Do not commit generated reports, market data, trade exports, secrets, or account-specific private data.
- Add or update focused tests for code changes.
- Run the test wrapper before committing.

```bash
./scripts/tl_test.sh
PYTHONDONTWRITEBYTECODE=1 python -B scripts/audit_repo.py
```

Financial-modeling changes should include validation output or diagnostics. Do not treat a model as actionable merely because it produces a probability.
