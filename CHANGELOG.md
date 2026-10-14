# Changelog

All notable changes to this project are documented here.

## [0.2.11] - 2026-10-13

### Added
- News collection from Alpaca's free Benzinga feed: `news_items` table (migration 002), raw page saved first, paging followed, reruns add nothing
- `trading` command: `migrate`, `check-brokers` (read-only Alpaca check), `ingest-news`
- Tests: 17 passing (news paging/raw-first/idempotency, edited stories, missing keys, sub-$1 orders)

### Changed
- Orders worth under $1 are skipped for every portfolio (Alpaca's minimum, verified on paper)
- Verified on paper: fractional day limit orders accepted; free plan includes the news feed

## [0.2.10] - 2026-10-12

### Added
- System design plan: slow themes layer, pivotal-event path, multi-pipeline virtual portfolios at $5,000 and $100,000, technical indicators, low-cost data set
- Phase 1 foundations code: Postgres schema (point-in-time bars, raw responses, links, themes, portfolios, orders, fills, run steps, pivotal events, hash-chained append-only audit log), ledger, shared cost model, basic risk gate, 12-1 momentum, pipeline definitions, Alpaca paper adapter, reconciliation, restartable evening run
- Tests: 13 passing against local Postgres

### Changed
- Requirements: Claude places paper orders behind the risk gate; Claude via Max subscription; themes (FR13), pivotal events (FR14), portfolio variants (FR15), indicators (FR2.4); low-cost paper data; phases updated

## [0.1.11] - 2026-10-11

### Changed
- Recorded Alpaca multi-leg options support (verified) and its order constraints in the requirements doc

### Removed
- Stale "Requirements from Research" copy; the revised requirements doc is the single source

## [0.1.10] - 2026-10-11

### Added
- GSD-T onboarding scaffold (progress, backlog, living docs, project CLAUDE.md, .gitignore)
- AI Trading System requirements doc (revised: owner-judged go-live, LLM-off definition, order timing, citation IDs, Postgres, dated links table) and the October 2026 research report

## [0.1.0] - 2026-10-11

### Added
- Initial changelog created by GSD-T
