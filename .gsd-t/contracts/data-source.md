# Data Source Contract

Every provider sits behind an adapter (DR1) in `src/trading/data.py`.

| Method | Output | Rules |
|---|---|---|
| `fetch_daily_bars(day)` | (request description, raw body) | Raw body is saved by `ingest` before parsing (DR2). Missing data raises. |
| `parse(body)` | list of `Bar` | Pure; no network. |
| `name` | provider name | Stored as `source` on every row. |

`ingest` stamps every row with `known_at`; readers pass an `as_of` time and see only rows known by then (FR1.1).
Implementations: `FixtureSource` (recorded sample data). Provider adapters (FMP, FRED, theme sources) follow this shape.

## News sources (`src/trading/news.py`)

| Method | Output | Rules |
|---|---|---|
| `fetch_pages(start, end)` | yields (request description, raw body) per page, oldest first | Follows the provider's paging until done. Raw page saved by `ingest` before parsing. |
| `parse(body)` | list of `Story` | Pure; no network. |
| `name` | provider name | Stored as `source` on every `news_items` row. |

A story is unique by (source, provider id, updated_at): an edited story is kept as a new row. `known_at` is when we fetched it.
Implementations: `AlpacaNews` (Benzinga stories, free plan, keys `ALPACA_PAPER_1_*`).
