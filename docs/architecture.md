# Architecture — TradingInvestments

## Last Updated: 2026-10-12

The design and its decision tree live in `.gsd-t/pseudocode/PseudoCode-TradingSystemDesign.md`;
requirements in `docs/AI Trading System — Requirements.md`. Interfaces: `.gsd-t/contracts/`.

## Components (Phase 1, `src/trading/`)

| Module | Purpose |
|---|---|
| `db.py`, `migrations/` | Postgres connection and schema migrations |
| `raw_store.py` | Saves every provider answer before parsing |
| `data.py` | Data adapters, point-in-time bar storage and reads, quality checks |
| `ledger.py` | Positions, cash and equity per virtual portfolio, derived from fills |
| `costs.py` | Shared cost model (spread, slippage, commission, volume cap) |
| `risk.py` | Basic risk gate: name weight, liquidity, daily loss stop |
| `momentum.py` | 12-1 month momentum ranking and equal-weight targets |
| `variants.py` | Pipeline definitions; seeds each at $5,000 and $100,000 |
| `broker.py` | Alpaca paper adapter and test fake |
| `reconcile.py` | Ledger vs broker check; mismatch halts |
| `pipeline.py` | Restartable evening run: ingest, quality, fills, decide, submit, reconcile |
| `audit.py` | Append-only, hash-chained audit log |

## Design Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-12 | Positions and cash derived from fills | Cannot drift from the trade record |
| 2026-10-12 | Ledger fills at the open or limit, with spread and slippage as an explicit cost | Same cost for every portfolio; respects the limit |
| 2026-10-12 | Each test runs in a throwaway Postgres schema | Real database behavior, nothing left behind |
