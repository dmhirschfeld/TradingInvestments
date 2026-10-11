# TradingInvestments

Trading and investments project — greenfield; scope to be defined in the first milestone.

> Everything general lives in `~/.claude/CLAUDE.md` and applies here. This file
> holds only what is true of this project and nothing else.

## Rules that can never be broken

None yet — no code or project-specific rules exist. Add them as the first
milestone settles them.

## Stack and commands

Not chosen yet. Decide during `/gsd-t-project` or the first `/gsd-t-milestone`.

| | |
|---|---|
| Build | `TBD` |
| Test | `TBD` |
| Expected branch | `main` |

## Logging

Trace and audit both use local SQLite (approved 2026-10-10): `.gsd-t/trace.db`,
`.gsd-t/audit.db`. Choice recorded in `.gsd-t/logging-scaffold-choice.json`.

## Where things are written down

| | |
|---|---|
| State and decisions | `.gsd-t/progress.md` |
| Interfaces between parts | `.gsd-t/contracts/` |
| How to reach environments | `docs/infrastructure.md` |

<!--
  Written 2026-10-10 at onboarding (empty repo, no scan).
  Regenerate with /gsd-t-setup once code exists.
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
