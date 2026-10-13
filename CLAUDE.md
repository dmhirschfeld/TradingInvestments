# TradingInvestments

Python paper-trading system: Claude-driven and rule-based pipelines run side by side as virtual portfolios ($5,000 and $100,000 sets). Design: `.gsd-t/pseudocode/PseudoCode-TradingSystemDesign.md`; requirements: `docs/AI Trading System — Requirements.md`.

> Everything general lives in `~/.claude/CLAUDE.md` and applies here. This file
> holds only what is true of this project and nothing else.

## Rules that can never be broken

- Every stored fact carries `known_at`; reads for a past decision use only what was known then.
- Save the raw provider answer (`raw_store.save`) before parsing it.
- Positions and cash are derived from fills in the ledger, never stored separately.
- `audit_log` is append-only and hash-chained; never update, delete or truncate it.
- Data-quality failure or ledger/broker mismatch stops the run; no step continues past it.
- Claude is called through Claude Code non-interactive mode on David's Max subscription; no `ANTHROPIC_API_KEY` in the job environment. Single user only.

## Stack and commands

Python 3.12 with uv, Postgres 17 (local Homebrew), psycopg, httpx, pytest.

| | |
|---|---|
| Install | `uv sync` |
| Test | `uv run pytest` (needs local database `trading_test`) |
| Migrate | `uv run python -c "from trading import db; db.migrate(db.connect())"` with `TRADING_DATABASE_URL` set |
| Expected branch | `main` |

## Logging

GSD-T tooling trace and audit use local SQLite (approved 2026-10-10): `.gsd-t/trace.db`,
`.gsd-t/audit.db`. Choice recorded in `.gsd-t/logging-scaffold-choice.json`.
The trading system's own audit log is the `audit_log` table in Postgres (FR11) — separate.

## Where things are written down

| | |
|---|---|
| State and decisions | `.gsd-t/progress.md` |
| Interfaces between parts | `.gsd-t/contracts/` |
| How to reach environments | `docs/infrastructure.md` |

<!--
  Written 2026-10-10 at onboarding (empty repo, no scan).
  Regenerate with /gsd-t-init-scan-setup once code exists.
-->


# Destructive Action Guard (MANDATORY)

**NEVER perform destructive or structural changes without explicit user approval.** This applies at ALL autonomy levels.

Before any of these actions, STOP and ask the user:
- DROP TABLE, DROP COLUMN, DROP INDEX, TRUNCATE, DELETE without WHERE
- Renaming or removing database tables or columns
- Schema migrations that lose data or break existing queries
- Replacing an existing architecture pattern (e.g., normalized → denormalized)
- Removing or replacing existing files/modules that contain working functionality
- Changing ORM models in ways that conflict with the existing database schema
- Removing API endpoints or changing response shapes that existing clients depend on
- Any change that would require other parts of the system to be rewritten

**Rule: "Adapt new code to existing structures, not the other way around."**
