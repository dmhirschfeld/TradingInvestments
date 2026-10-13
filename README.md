# TradingInvestments

Paper-trading system that runs Claude-driven and rule-based pipelines side by side as virtual portfolios.

```bash
uv sync
createdb trading && createdb trading_test
uv run pytest
```

Copy `.env.example` to `.env` and fill in values as accounts are created.

## Status
- Version: see `.gsd-t/progress.md`
- Managed with [GSD-T](https://github.com/Tekyz-Inc/get-stuff-done-teams)

## Docs
- Requirements: `docs/AI Trading System — Requirements.md`
- Design plan: `.gsd-t/pseudocode/PseudoCode-TradingSystemDesign.md`
- Architecture: `docs/architecture.md`
- Workflows: `docs/workflows.md`
- Infrastructure: `docs/infrastructure.md`
