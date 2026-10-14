# Trading System Design

How the paper-trading system watches the market, slow themes and rare pivotal events, and runs several virtual portfolios side by side so the best approach shows itself over time.

```text
Every evening after the US close
  Pull the day's prices, fundamentals, news and theme data
  Save each raw answer before reading it, stamped with when we learned it
  Does the data pass the quality checks (gaps, stale prices, splits):
    No:  Block trading for the day and alert David
    Yes: Carry on
  Work out the standard chart readings for every stock (trends, momentum, swings, volume, candle shapes)
  Smooth each theme at its own natural pace
    El Niño outlooks over months, election odds over weeks, online chatter over days to weeks
  Has a theme held the same direction long enough:
    No:  Treat it as noise
    Yes: Mark it as an active theme, with its direction and strength
  Narrow the whole market to a daily shortlist
  For each virtual portfolio (each one is its own pipeline with its own pretend cash)
    Does this portfolio use Claude:
      No:  Its fixed rules pick the trades (momentum, random picks, index holders)
      Yes: Claude reads the facts it is given, each with a tag it must cite
           Does this portfolio show Claude the themes:
             Yes: Include the active themes
             No:  Leave them out
           Claude writes a thesis per stock: which way, how sure, how long, what would prove it wrong
           Does every number Claude cites match its source:
             No:  Discard the thesis and log why
             Yes: Keep it
           Who decides the size of each trade:
             The formula: size from how jumpy the stock is and how sure Claude is
             Claude:      use Claude's own size
    Does this portfolio go through the risk check (hard limits on size, sector, liquidity, daily losses):
      Yes: The check can veto any order, and each veto is logged with the rule that fired
      No:  Orders go straight through (this is one of the tests, paper only)
    Record the orders in the ledger (our own book of every portfolio's trades)
  Is this portfolio one of the three mirrored on Alpaca paper:
    Yes: Claude places the orders through the broker, as limit orders for the next open
    No:  The ledger fills them using the shared cost model
  Does Alpaca's account match the ledger:
    No:  Stop trading and alert David
    Yes: Mark the step done

All day while markets are open
  Watch the news stream, and the market for sudden shocks
  Did a major story break (war, attack, bailout, emergency Fed move):
    Do two independent credible sources confirm it:
      No:  Hold it as unconfirmed and alert David
      Yes: Claude rates it against the written pivotal scale
        Does it clear the bar:
          No:  Pass it to the themes as an ordinary story
          Yes: Pivotal event
  Did the market show a shock with no story yet:
    Yes: Freeze new buying, alert David, keep looking for the cause
  Pivotal event
    Alert David at once
    Claude writes an emergency thesis: who wins, who loses, for how long
    One copy of each portfolio acts on it automatically, the other logs what it would have done after waiting for David
    Has the pivotal bar fired more than a few times this year:
      Yes: The bar is too low; raise it
      No:  Keep it

Every day
  Score every portfolio the same way: gain, risk, worst drop, cost paid
  Discount the best scores for how many portfolios were tried, so luck does not look like skill
  Show them side by side on the dashboard
```

---

## What it does today

```text
Nothing runs yet
  There are requirement documents and a research report
  The requirements say Claude only proposes trades and code places them
  They list news as the only outside signal, starting in Phase 3
  They test Claude against one version of the same system with Claude switched off
```

It got this way because the first design aimed to prove one thing, whether Claude adds value, with as little machinery as possible.

## What changes

```text
Claude places the paper orders itself
  The risk check still sits in front of most portfolios
  Whether Claude may place real-money orders is decided later, after the paper record exists

Several virtual portfolios instead of one Claude portfolio
  Who sizes the trade:  the formula, or Claude
  Is the risk check on:  yes, or no
  Does Claude see themes:  yes, or no
  Does it use candle shapes:  yes, or no
  Plus the fixed yardsticks:  SPY, IWM, momentum, Claude switched off, random picks
  Every one of these runs twice: once starting with $5,000, once with $100,000
    Same decisions from Claude, so the only difference is account size
  Three of them are mirrored on Alpaca paper, the rest live only in the ledger

A slow themes layer
  Climate, election and policy odds, Fed rate path, tariffs, commodity cycles, demographics, news tone, online chatter, innovation (patents, drug approvals, trials)
  Each one is smoothed at its own pace, and only a lasting trend counts
  Themes inform Claude's reasoning; they do not move money by a fixed rule unless that test portfolio says so

A rare pivotal-event path
  A news story or a market shock can set it off; news needs two sources
  Market-shock buying freeze arrives in Phase 2, news trigger logged in Phase 3, acted on in Phase 4
  The detector itself runs and logs from Phase 1

Phase 1 grows
  The whole market, not a handful of symbols, so history starts on day one
  Momentum trades on Alpaca paper from the start, so the ledger has real trades to match
  A basic risk check comes with it, because nothing trades without limits
  Theme, news and pivotal-event data is collected from day one
```

## The rules

- [RULE] Every stored fact carries when we learned it; a past decision only sees what was known then.
- [RULE] Raw answers from every source are saved before they are read, so they can be reprocessed.
- [RULE] Every number Claude uses carries a tag; a thesis citing a number that does not match its source is thrown out.
- [RULE] All portfolios share the same data, shortlist and cost model, so results compare like for like.
- [RULE] Any data-quality failure or ledger mismatch with Alpaca stops trading that day, loudly.
- [RULE] Every daily run can be rerun or restarted from its last finished step without doubling anything.
- [RULE] Each data provider sits behind its own adapter (a swappable plug-in) so it can be replaced without touching strategy code.
- [RULE] Claude may place paper orders; real-money orders by Claude are a later decision with their own guardrails.
- [RULE] Pivotal events need two independent sources for a news trigger; the bar is kept rare by counting how often it fires.
- [RULE] Postgres holds the trading data, ledger, audit log and the links table; no graph database unless link queries prove slow.
- [RULE] Secrets live in the environment or a vault, never in code or logs.
- [RULE] Claude is called through Claude Code's non-interactive mode on David's own subscription login; a paid API key must never be present in the job's environment, and a usage-limit hit stops the step loudly and resumes from it later.
- [RULE] The app serves David only; it is never shared or run for anyone else while it uses the subscription login.

## What I confirmed with you

- Stack as in the requirements: Python 3.12 with uv, Postgres, cron plus step records, the Anthropic Python library, Streamlit, Alpaca paper behind an adapter.
- Claude places orders on paper; real money is a later call.
- Build pipelines for all three order styles (formula sizes; Claude sizes; Claude sizes with no risk check) as separate virtual portfolios, and compare them over time.
- Themes: test both "reasoning only" and "automatic tilt"; smoothing varies by theme.
- Themes tracked: climate, elections and policy, news trends, online sentiment, Fed path, tariffs, commodities, demographics, innovation.
- Not a reactive engine; slow trends steer, rare pivotal events can act quickly. A news story alone can trigger a pivotal event.
- A few minutes of news delay is fine. Pivotal trades are automatic on paper, with a "wait for David" copy logged for comparison.
- Momentum trades on Alpaca paper in Phase 1; the full market is collected from Phase 1; theme data is collected from Phase 1.
- Trading audit log in Postgres, separate from the GSD-T tooling log.
- Standard chart indicators and candle patterns are included.
- Use the existing local Postgres 17 (Homebrew) with a new database of its own; no accounts exist yet.
- Low-cost data while paper trading (~$49/mo); upgrade only when a paper test proves a source is needed.
- Claude runs on David's Max subscription (single user, personal use), not a paid API key.
- Two sets of every pipeline: one starting with $5,000 of pretend cash (close to the planned first live amount) and one with $100,000, compared in percentages to see whether account size changes results.
- Alpaca mirrors three portfolios: momentum, Claude with formula sizing, Claude with its own sizing (both with the risk check), from the $5,000 set.
- No further checks on using the Max plan; David has run many personal apps this way.

## Why this shape

- Objective: find which decision pipeline makes the best risk-adjusted return, consistently, on paper, before any real money.
- Conflict: Claude placing orders breaks the old "code places orders" rule. Kept fair by routing every Claude portfolio except the no-check test through the same risk check as the yardsticks.
- Reuse: one daily data load and one shortlist feed every portfolio; one Claude call serves all sizing variants, so only the themes on/off split adds Claude cost.
- Simplicity: portfolios are rows in one ledger, not separate systems. Alpaca allows three paper accounts per person, so three are mirrored and the rest are tracked by our own ledger.
- Duplication: the pivotal path reuses the risk check, kill switch and daily loss stop already in the requirements.
- Risk: more portfolios means more chances that one looks good by luck; the deflated score (which discounts for how many were tried) already in the requirements handles this, but it needs a longer paper run.
- No fallback: data failures, ledger mismatches and citation failures stop the step loudly; nothing degrades quietly.
- Data limbo: unconfirmed news is held visibly and reported to David, not silently parked.

## Data sources chosen (research, Oct 12, 2026; low-cost while paper trading)

Paper trading runs on the cheapest set (~$49/mo for data). A paid source is added only when a paper test shows it is really needed.

| Need | Source | Cost per month |
|---|---|---|
| Broker, fast news stream | Alpaca free plan (paper trading; news stream on free plan to confirm). Paid $99 data plan deferred | Free |
| End-of-day prices and volume (whole market), fundamentals, delisted companies | Financial Modeling Prep lower tier (confirm it covers delisted and bulk end-of-day) | ~$49 |
| Macro, Fed path, jobs, inflation, consumer mood (with past versions) | FRED / ALFRED | Free |
| Climate | NOAA El Niño discussions and seasonal outlooks | Free |
| Commodities | EIA energy data, USDA crop reports | Free |
| Election and policy odds | Kalshi (and Polymarket, legality to confirm) | Free |
| Tariffs | Yale Budget Lab tariff tracker, Census trade data | Free |
| News tone and world-event cross-check | GDELT | Free |
| Innovation | Patent office bulk data, openFDA, ClinicalTrials.gov | Free |
| Search interest for themes | SerpApi free tier, 250 searches/mo, weekly theme terms only (apply for Google's Trends API too) | Free |
| Public attention per company | Wikipedia page views (Wikimedia API) | Free |
| Online chatter | Deferred (Quiver ~$75/mo) until proven needed; GDELT news tone covers part of it | Free |

Sources: CPC El Niño discussion https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml (Oct 8, 2026); ALFRED vintages https://fred.stlouisfed.org/docs/api/fred/fred_vs_alfred.html; Kalshi history https://docs.kalshi.com/getting_started/historical_data; GDELT https://www.gdeltproject.org/about.html; Alpaca news stream https://docs.alpaca.markets/docs/streaming-real-time-news; Alpaca has no historical asset list https://forum.alpaca.markets/t/delisted-tickers/18227; Alpaca three paper accounts https://forum.alpaca.markets/t/feature-request-more-paper-trading-accounts/18125; USPTO PatentsView move https://www.uspto.gov/subscription-center/2026/patentsview-migrating-uspto-open-data-portal-march-20.

## Two account sizes ($5,000 and $100,000)

- Both sets share the same Claude theses and data; only sizing and fills differ, so the second set adds no Claude usage.
- Results are compared as percentages; the differences to expect come from fractional shares, options access, order minimums and cost drag on small orders.

At $5,000:

- Positions start at about 8, roughly $600 each, using fractional shares (parts of a share).
- The options sleeve is tiny at this size: the 2% risk limit allows about $100 at risk per option trade, so options wait until the account grows or stay at one small spread.
- Bid-ask spreads (the gap between buy and sell price) weigh more on small orders; the shared cost model already charges them.

## How Claude is called

- Claude Code's non-interactive mode (one command per request) with a one-year login token from David's Max plan, and structured answers checked against a fixed shape.
- Allowed for one person's own automation; not allowed for an app offered to others (https://code.claude.com/docs/en/legal-and-compliance).
- No half-price overnight batch on a subscription, so the batch and caching line in the requirements is dropped.
- Usage limits run in 5-hour and weekly windows; a limit hit stops the step loudly and it resumes from there.

## Open questions

- Financial Modeling Prep lower tier: confirm it includes whole-market end-of-day prices and delisted history before paying.
- ~~Alpaca free plan: confirm it includes the live news stream.~~ Confirmed 2026-10-13.
- ~~Whether Alpaca accepts limit orders for fractional shares.~~ Yes, day limit orders; orders under $1 are rejected (confirmed 2026-10-13).
- Polymarket read access from the US: confirm it is allowed, else Kalshi only.
- Alpaca news covers Benzinga staff stories only; if it misses world events, add Finnhub's general news.
- Candle-pattern evidence is unproven; it is tested as its own portfolio rather than trusted.

---

## Where it lives

- Requirements to update: `docs/AI Trading System — Requirements.md` (core principle, FR4, FR5, FR8, FR12, data table, phases, new FR sections for themes and pivotal events, technical indicators).
- Planned layout (Python package, nothing exists yet): `src/trading/` with `data/` (one adapter per provider), `features/` (indicators, theme smoothing), `screener/`, `research/` (Claude calls, citation check), `portfolios/` (variant definitions), `risk/`, `broker/` (Alpaca adapter), `ledger/`, `pivotal/` (news watcher), `audit/`, `dashboard/`.
- Database: new `tradinginvestments` database on the local Postgres 17 (Homebrew); record its row in `docs/infrastructure.md` under Environments.
- Contracts to write in `.gsd-t/contracts/`: thesis output shape, portfolio variant definition, broker adapter interface, data adapter interface.
