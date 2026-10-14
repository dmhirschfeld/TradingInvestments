# GSD-T Progress

## Project: TradingInvestments
## Version: 0.2.11
## Status: IN PROGRESS
## Date: 2026-10-12 18:22 PDT

## Current Milestone
Phase 1 Foundations — branch phase1-foundations. Done: schema, ledger, cost model, basic risk gate, momentum, variants, Alpaca adapter, reconciliation, restartable run (13 tests). Next: FMP/FRED/theme data adapters, pivotal-event logger, cron entry, Alpaca keys and live reconcile gate.

## Completed Milestones
| Milestone | Version | Completed | Tag |
|-----------|---------|-----------|-----|
<!-- M59: "Completed" cell format is `YYYY-MM-DD HH:MM TZ` for entries written ≥ v3.29.10; older rows may be `YYYY-MM-DD`. Readers MUST accept both. -->


## Domains
| Domain | Status | Tasks | Completed |
|--------|--------|-------|-----------|
(populated during partition phase)

## Contracts
(populated during partition phase)

## Integration Checkpoints
(populated during plan phase)

## Blockers
<!--
### [Blocker description]
- **Found**: [date]
- **Attempted**: [what was tried]
- **Status**: investigating | waiting | resolved
-->

## Decision Log
- 2026-10-10 16:29: Project initialized with GSD-T workflow (greenfield; remote github.com/dmhirschfeld/TradingInvestments, empty)
- 2026-10-10 16:33: Onboarding — logging backend local-sqlite approved by user; .gitignore added; project CLAUDE.md written; scan skipped at user request (empty repo)
- 2026-10-10 22:40: Requirements doc revised — go-live is now owner judgment (no 6–12 month gate); LLM-off defined; controls run in internal ledger; order timing (FR8.4); citation IDs (FR5.3); go-live view (FR12.4); Postgres chosen; cron over Prefect; data subscriptions staged by phase; pipeline steps listed
- 2026-10-11 12:01: Merged links-table (FR1.4), no-graph-DB rule (FR1.5), Phase 1 links table and Phase 4 related-names experiment from "Requirements from Research.md" into the revised requirements doc
- 2026-10-11 13:07: Research report reviewed — no graph-DB recommendation in its body; resolved Alpaca free-plan question (IEX-only, keep $99 plan) in requirements doc
- 2026-10-11 13:20: Initial check-in to GitHub (v0.1.10) — onboarding scaffold, requirements docs, research report
- 2026-10-11 13:24: Deleted stale "Requirements from Research.md" (user-approved); verified Alpaca paper supports multi-leg options (mleg) and recorded constraints in requirements doc (v0.1.11)
- 2026-10-12 18:03: Architect pass on system design — added slow themes layer, pivotal-event path, multi-portfolio variant testing (Claude places paper orders), technical indicators, full-universe + theme data from Phase 1; data sources researched; plan in .gsd-t/pseudocode/PseudoCode-TradingSystemDesign.md awaiting approval
- 2026-10-12 18:08: Paper phase switched to low-cost data (~$49/mo): Alpaca free plan, FMP lower tier for end-of-day prices, SerpApi free tier, Wikipedia page views; Alpaca $99 and Quiver deferred until proven needed
- 2026-10-12 18:11: Claude via Max subscription (claude -p, personal use, no API key in job env, HALT on limit); $5,000 starting cash per portfolio; Alpaca mirrors momentum + Claude formula-sized + Claude self-sized
- 2026-10-12 18:12: Every pipeline runs at two sizes ($5,000 and $100,000), compared in percent; Alpaca mirrors come from the $5,000 set; Max-plan checks dropped at user direction
- 2026-10-12 18:22: Built Phase 1 foundations on branch phase1-foundations (v0.2.10): requirements doc revised to the approved plan; Postgres schema, ledger, cost model, basic risk gate, momentum, 22 portfolio definitions, Alpaca paper adapter, reconciliation, restartable evening run; 13 tests pass; local DBs trading / trading_test recorded in Environments
- 2026-10-13 10:23: Committed Phase 1 foundations on phase1-foundations and pushed the branch; 13/13 tests pass; merge to main pending
- 2026-10-13 17:07: Branch phase1-data-feeds (v0.2.11): Alpaca paper accounts 1 and 2 verified; fractional day limit orders confirmed, $1 order minimum found and enforced for all portfolios; Alpaca free plan news feed confirmed and collected into news_items; `trading` CLI (migrate, check-brokers, ingest-news); real `trading` DB migrated, 22 portfolios seeded; 17/17 tests pass. FMP/FRED keys and Alpaca account 3 still pending

## Session Log
| Date | Session | What was accomplished |
|------|---------|----------------------|
| 2026-10-10 16:29 PDT | 1 | Project initialized |
<!-- M59: "Date" cell format is `YYYY-MM-DD HH:MM TZ` for entries written ≥ v3.29.10; older rows may be `YYYY-MM-DD`. Readers MUST accept both. -->

