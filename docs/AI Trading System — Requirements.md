# AI Trading System — Requirements

Oct 10, 2026 · revised Oct 12, 2026 · @David Hirschfeld

## Summary

Build a Python system that paper-trades US stocks, ETFs and defined-risk options on its own, using Claude Opus 5.5 for research and decisions, and runs many decision pipelines side by side as virtual portfolios so the best approach shows itself over time. Holding periods run from about one week to several months; no day trading.

- **Core principle:** Claude decides and, on paper, places its own orders; code supplies the facts, checks every cited number, and (in every portfolio except the no-check test) runs the risk gate in front of the broker. Whether Claude may place real-money orders is decided after the paper record exists, with its own guardrails.
- **Not a reactive engine:** slow, smoothed themes steer decisions; only rare, confirmed pivotal events act quickly (FR13, FR14).
- **Phase 1 scope:** simulated portfolio only (Alpaca paper plus an internal ledger). Real money only when David judges the system is working as expected (see Go-live decision).
- **Success:** beat SPY and IWM on risk-adjusted return after costs, and beat the same pipeline with Claude turned off. Tripling the benchmark is upside, not the target.
- **Build:** executed with GSD-T.

## Goals, non-goals and metrics

The system must prove Claude adds measurable value over cheap baselines before any real money is used.

**Goals**

- G1. Trade autonomously on paper across large, mid and small caps, ETFs, and defined-risk options.
- G2. Switch strategy posture with market regime (trend, volatility, credit conditions).
- G3. Log every decision so any trade can be explained and replayed.
- G4. Measure Claude's contribution against shadow portfolios that run the same rules without it.
- G5. Track slow themes (climate, elections and policy, Fed path, tariffs, commodities, demographics, news tone, online sentiment, innovation), smoothed so short spikes do not drive decisions.
- G6. Act quickly on rare, confirmed pivotal events (war, attack, bailout, emergency Fed action).
- G7. Compare decision pipelines and two account sizes ($5,000 and $100,000) as virtual portfolios on the same data.

**Non-goals (phase 1)**

- Same-day round-trip trading.
- Naked short options, margin leverage above 1.0x gross for longs.
- Live money, multi-user support, or managing anyone else's capital.

**Benchmarks and metrics**

| Benchmark | Purpose |
| --- | --- |
| SPY total return | Primary market benchmark |
| IWM total return | Small-cap benchmark, since the universe includes small caps |
| Momentum baseline | Shows whether a cheap rules-based strategy does as well |
| LLM-off pipeline | Same screener, sizing and risk, no Claude; isolates Claude's value |
| Random-entry control | Same sizing and risk, random picks; detects luck |

**LLM-off pipeline definition.** It picks from the same daily shortlist Claude reviews. Direction is long; conviction 1–5 is the screener's composite-score quintile; horizon is a fixed 60 trading days; exit on the same volatility-based stop. This keeps the only difference between it and the Claude portfolio the Claude decision itself.

**All benchmark, control and variant portfolios run in the internal ledger** with one shared cost model, so every comparison is like for like (FR15). Alpaca allows three paper accounts per person; they mirror three portfolios from the $5,000 set (momentum, Claude with formula sizing, Claude with its own sizing), and their job is to check the ledger against a real broker's fills.

Metrics tracked daily for every portfolio: total return, excess return, Sharpe, Sortino, max drawdown, volatility, hit rate, average win/loss, turnover, and costs paid.

## Architecture

A daily pipeline runs after the US close; Claude appears in three steps, and every step that touches money is code.

&#91;embedded content: daily pipeline · 12 components, Claude in 3\]

Pipeline steps in order (★ = Claude):

1. Data store — ingest and quality-check the day's data, including theme data
2. Indicators and themes — standard chart indicators per stock; each theme smoothed at its own pace (FR13)
3. Screener — universe to 50–150 candidates plus current holdings
4. Regime classifier — sets exposure limits and active sleeves
5. ★ Triage (Haiku/Sonnet) — news and filings cut candidates to a shortlist
6. ★ Deep research (Opus 5.5) — bull/bear thesis JSON per shortlisted name and open position
7. Portfolio construction — target weights per variant portfolio (FR15)
8. Risk gate — hard veto on every proposed order (skipped only by the no-check test portfolio)
9. Execution — broker adapter places orders for the three mirrored portfolios
10. Internal ledger — records fills, costs and positions for every portfolio
11. ★ Reflection — post-mortem on each closed trade
12. Audit log — append-only record of every step
13. Evaluation and dashboard — all portfolios side by side, metrics, alerts

Running alongside during market hours: the ★ pivotal-event watcher (FR14).

Claude's theses feed sizing, never the broker directly. The regime classifier also sets the risk gate's exposure limits, and the ledger feeds both evaluation and Claude's post-trade reflection.

## Functional requirements

Each component has one owner of truth; only the execution adapter talks to the broker.

**FR1 Data store**

- FR1.1 Store every record with an as-known-at timestamp; queries return only what was known at the decision time.
- FR1.2 Store fundamentals as reported, never restated; keep delisted symbols.
- FR1.3 Ingest on a schedule after the US close, with retries and data-quality checks (gaps, stale prices, splits).
- FR1.4 Store relationships in one Postgres links table: from-entity, to-entity, link type, valid-from, valid-to, known-at, source. It covers companies, funds, insiders, news, sectors and macro factors under the same point-in-time rule.
- FR1.6 Collect theme and news data from phase 1 so its history builds from day one; most sources overwrite revisions, so our own daily snapshot is the point-in-time record.
- FR1.5 No separate graph database. Add graph queries ([Apache AGE](https://age.apache.org/)) only if traversal queries become deep or slow; [Neo4j](https://neo4j.com/) is the last resort.

**FR2 Screener**

- FR2.1 Reduce a universe of large, mid and small caps plus ETFs to 50–150 daily candidates.
- FR2.2 Factors: momentum, quality, value, volatility; filters on minimum price, average dollar volume and spread.
- FR2.3 Always include current holdings for re-review.
- FR2.4 Compute standard indicators from daily bars: moving averages and crossovers, MACD, RSI, rate of change, relative strength vs sector and SPY, ATR, Bollinger Bands, volume trend, on-balance volume, support and resistance, 52-week highs and lows, gaps, and daily and weekly candlestick patterns. Each value carries an ID so Claude can cite it.

**FR3 Regime classifier**

- FR3.1 Classify the market into discrete regimes from trend (SPY vs 200-day average), VIX level and term structure, credit spreads, yield curve and breadth.
- FR3.2 Each regime sets gross/net exposure limits and which strategy sleeves are active.
- FR3.3 Claude may write a regime narrative but cannot change the classification.

**FR4 Triage (Haiku or Sonnet)**

- FR4.1 Scan news and new filings for each candidate and cut to a shortlist for deep review.

**FR5 Deep research (Opus 5.5)**

- FR5.1 Run a bull/bear analysis per shortlisted name and per open position.
- FR5.2 Output validated JSON: ticker, direction, conviction 1–5, horizon, instrument (stock or option structure), catalysts with dates, thesis, invalidation conditions, key risks, data citations.
- FR5.3 Reject any output that fails the schema or cites numbers not in the input data. Every input number carries an ID; Claude cites IDs, and a validator checks each cited value against its source record.
- FR5.4 Pin the model version; log it on every call.
- FR5.5 Call Claude through Claude Code's non-interactive mode on David's Max subscription (single user, personal use) with a structured-output schema. No paid API key may be present in the job environment. A usage-limit hit stops the step loudly; the run resumes from it.
- FR5.6 One Claude thesis per name serves every sizing variant; only the themes on/off split needs a second call.

**FR6 Portfolio construction**

- FR6.1 Size by volatility target × conviction multiplier, capped by fractional Kelly.
- FR6.2 Target 8–15 positions; per-name cap 10–15%; per-sector cap 25–30%.
- FR6.3 Options sleeve capped at 10–20% of equity, defined-risk structures only.
- FR6.4 Fractional shares are allowed so small portfolios ($5,000) can hold about 8 positions.

**FR7 Risk gate** (see Risk management)

**FR8 Execution**

- FR8.1 Place limit orders through the broker adapter with idempotent client order IDs. On paper, Claude places orders through a tool that runs the risk gate first.
- FR8.2 Reconcile broker positions against the internal ledger daily; halt on mismatch.
- FR8.3 Broker adapter is an interface: Alpaca paper first, Interactive Brokers later.
- FR8.4 Order timing: orders are submitted before the next open as day-only limit orders, priced at the prior close plus or minus a configurable band. Unfilled orders expire and are re-evaluated by the next evening's run.

**FR9 Internal ledger**

- FR9.1 Source of truth for the simulated portfolio.
- FR9.2 Model spread, slippage, commissions, borrow fees, dividends and a fill cap as a percentage of average daily volume.

**FR10 Reflection**

- FR10.1 On each closed trade, Claude writes a post-mortem stored for retrieval.
- FR10.2 A lesson changes rules or prompts only after it recurs across multiple trades and a human approves it.

**FR11 Audit log**

- FR11.1 Append-only record of data snapshot hashes, prompts, model ID, raw and parsed outputs, risk decisions, orders and fills.
- FR11.2 Any day can be replayed from the log.

**FR12 Evaluation and dashboard**

- FR12.1 Run all shadow portfolios daily on the same data, in the internal ledger.
- FR12.2 Dashboard shows equity curves, metrics, open positions with theses, and attribution.
- FR12.4 Go-live view: one screen with Claude vs LLM-off on the same shortlist (decision by decision), risk-adjusted return vs SPY and IWM, drawdown, and operational incidents. This is the evidence David uses to decide on going live.
- FR12.3 Alerts (Slack or email) for fills, risk-gate vetoes, circuit breakers, pivotal events and job failures.

**FR13 Themes**

- FR13.1 Track theme signals: climate (NOAA El Niño and seasonal outlooks), commodities (EIA, USDA), Fed path, jobs, inflation and consumer mood (FRED/ALFRED), election and policy odds (Kalshi; Polymarket if US read access is confirmed), tariffs (Yale Budget Lab tracker, Census trade), news volume and tone (GDELT), search interest (SerpApi, weekly theme terms), public attention per company (Wikipedia page views), innovation (patent office bulk data, openFDA, ClinicalTrials.gov).
- FR13.2 Refresh daily; smooth each theme at its own natural pace (months for climate, weeks for election odds, days to weeks for chatter).
- FR13.3 A theme becomes active only after its smoothed trend holds one direction long enough; otherwise it is noise.
- FR13.4 Active themes reach Claude as cited facts. An automatic tilt by fixed rule is a separate test portfolio, not the default.

**FR14 Pivotal events**

- FR14.1 During market hours, watch the Alpaca news stream (GDELT as a slower cross-check) and market shock signals (index-wide halts, sharp index drops, VIX jumps).
- FR14.2 A news trigger needs two independent credible sources; Claude rates it against a written pivotal scale with a high bar. Unconfirmed stories are held and reported to David.
- FR14.3 A market shock with no known cause freezes new buying and alerts David.
- FR14.4 A pivotal event alerts David and produces an emergency thesis (who wins, who loses, for how long). On paper one copy of each portfolio acts automatically; the other logs what it would have done after waiting for David.
- FR14.5 Count how often the bar fires; more than a few times a year means it is too low.

**FR15 Portfolio variants**

- FR15.1 Each pipeline is a virtual portfolio with its own cash, positions and daily value in the internal ledger.
- FR15.2 Pipelines: sizing by formula or by Claude; risk gate on or off (off is paper only); themes as reasoning only or with automatic tilt; candlestick patterns used or not; plus the yardsticks (SPY, IWM, momentum, LLM-off, random entry).
- FR15.3 Every pipeline runs twice, starting with $5,000 and with $100,000, compared in percentages to see whether account size changes results.
- FR15.4 Scores are discounted for how many pipelines were tried (deflated Sharpe, EV2).

## Data requirements

Paper trading runs on the low-cost set, about $49/mo for data; a paid source is added only when a paper test shows it is needed. Claude runs on David's existing Max subscription. Prices are from research on Oct 10–12, 2026; confirm at signup.

| Data | Provider | Price/mo | Phase |
| --- | --- | --- | --- |
| Broker, live news stream (Benzinga) | [Alpaca](https://docs.alpaca.markets/docs/streaming-real-time-news) free plan | Free | 1 |
| End-of-day prices and volume (whole market), fundamentals, delisted companies | [Financial Modeling Prep](https://site.financialmodelingprep.com/pricing-plans) lower tier (confirm delisted and bulk end-of-day coverage) | \~$49 | 1 |
| Stock + options prices (SIP, OPRA) | [Alpaca Algo Trader Plus](https://docs.alpaca.markets/us/docs/about-market-data-api) | $99 | Deferred until proven needed |
| Theme sources (FR13.1): NOAA, EIA, USDA, FRED/ALFRED, Kalshi, Yale tariff tracker, Census trade, GDELT, Wikipedia page views, patents, openFDA, ClinicalTrials.gov | Various | Free | 1 |
| Search interest for themes | [SerpApi](https://serpapi.com/pricing) free tier (250 searches/mo) | Free | 1 |
| News and analyst ratings | [Benzinga via Massive](https://massive.com/partners/benzinga) | $99 | Deferred; Alpaca's stream carries Benzinga |
| Insider, congressional and social (WallStreetBets) data | [Quiver Quantitative Trader](https://api.quiverquant.com/pricing/) | $75 | Deferred until proven needed |
| Filings, Form 4, 13F (primary) | [SEC EDGAR](https://www.sec.gov/edgar/search/) | Free | 1 |
| Macro and regime inputs | [FRED](https://fred.stlouisfed.org/) | Free | 1 |
| Point-in-time fundamentals | [Tiingo](https://www.tiingo.com/products/fundamental-data-api) | $30–80 | 1 (optional) |
| Implied volatility surfaces | [ORATS](https://orats.com/data-api) | $199–599 | 4 (options sleeve) |
| Options flow | [Unusual Whales API](https://unusualwhales.com/public-api) | \~$150–375 | Later, only if it proves useful |
| International data | [EODHD](https://eodhd.com/pricing) | $99.99 | Later |

- DR1. Each provider sits behind an adapter so it can be swapped without touching strategy code.
- DR2. Raw responses are stored before parsing, so data can be reprocessed.
- DR3. Survivorship-free history (including delisted names) is required for any deterministic backtest.
- DR4. Subscribe to each provider in the phase that first uses it (Phase column), not up front.
- DR5. From day one, the system's own daily snapshots are the point-in-time record. Vendor point-in-time fundamentals (Tiingo) are needed only to backtest the quality and value screens.

## Risk management

The risk gate is a hard veto that runs on every proposed order; no component, including Claude, can override it. Limits below are starting values, tuned from paper results.

| Rule | Starting value |
| --- | --- |
| Max weight per name | 10–15% |
| Max weight per sector | 25–30% |
| Options sleeve | ≤ 10–20% of equity; defined-risk only (spreads, collars, long options) |
| Max premium at risk per option trade | ≤ 2% of equity |
| Liquidity | Order ≤ 5% of 20-day average dollar volume |
| Shorts | Only when borrow is available; borrow cost modeled |
| Earnings blackout | No new stock position within 2 days before earnings unless the thesis is the earnings event |
| Per-position stop | Exit on invalidation condition or volatility-based stop |
| Daily loss circuit breaker | Halt new orders for the day |
| Market shock | Freeze new buying until the cause is known (FR14.3) |
| Portfolio drawdown limit | To be set after paper trading (open decision) |
| Kill switch | Manual, closes or freezes all activity |

- RM1. The gate logs every veto with the rule that fired.
- RM2. Gross and net exposure limits come from the regime classifier.
- RM3. Any data-quality failure or ledger mismatch blocks trading for that day.

## Evaluation and go-live decision

Claude is judged only on forward paper trading, because any backtest before its June 2026 knowledge cutoff is contaminated.

- EV1. Historical backtests are allowed only for deterministic parts: momentum baseline, regime classifier, sizing and risk rules.
- EV2. Every prompt or model change is logged as a new trial; results use the deflated Sharpe ratio to correct for multiple testing.
- EV3. Factor regression (market, size, momentum, quality) runs monthly to separate skill from beta and style tilts.
- EV4. Claude and the LLM-off pipeline are compared decision by decision on the same daily shortlist (which names each picks, and how those picks perform). This gives a usable signal far sooner than comparing portfolio Sharpe ratios.

**Go-live decision**

Going live is David's judgment, made when the system is working as expected. There is no fixed minimum duration or trade count. The go-live view (FR12.4) supplies the evidence:

- Claude vs LLM-off and random-entry, decision by decision and by portfolio
- Risk-adjusted return vs SPY, IWM and the momentum baseline, after modeled costs
- Drawdown, and any operational incidents
- First live allocation is a deliberately small amount

## Non-functional requirements and stack

The system is Python end to end, developed on Mac and run in production on a small cloud VM so it never misses a run because a laptop is asleep.

| Area | Choice |
| --- | --- |
| Language and packaging | Python 3.12, uv |
| Claude access | Claude Code non-interactive mode on David's Max subscription, structured-output schema (FR5.5) |
| Agent orchestration | Plain Python first; LangGraph only if the debate flow needs it |
| Storage | Postgres for point-in-time data, ledger and audit log (transactions for the ledger; the dashboard reads while the pipeline writes) |
| Analytics | pandas, statsmodels, hmmlearn; vectorbt for baseline backtests |
| Scheduling | Cron timer plus step-completion records in Postgres (meets NF2); Prefect only if this proves insufficient |
| Broker | [Alpaca](https://docs.alpaca.markets/us/docs/paper-trading) paper; [Interactive Brokers](https://www.interactivebrokers.com/en/pricing/commissions-home.php) for live |
| Dashboard and alerts | Streamlit; Slack or email alerts |
| Dev tooling | [Alpaca MCP server](https://github.com/alpacahq/alpaca-mcp-server) for interactive research in Claude Code only, never in the production loop |

- NF1. Secrets in a secrets manager or environment, never in code or logs.
- NF2. Every daily run is idempotent and restartable from the last completed step.
- NF3. Same code path for paper and live; only the broker adapter and config change.
- NF4. Test coverage required on sizing, risk gate, ledger and broker adapter, including fault injection.
- NF5. Claude runs on the Max subscription; a usage-limit hit stops the step loudly and the run resumes from it.
- NF6. Single user only; the app is never offered to anyone else while it uses the subscription login.

## Phases and open decisions

Each phase ends at a gate, not a date.

1. **Foundations:** data store for the whole market (including the links table and theme data), broker adapter, internal ledger with variant portfolios at both sizes, audit log, basic risk gate (per-name cap, liquidity, daily loss stop), momentum trading on Alpaca paper, SPY/IWM shadow portfolios, pivotal-event detector logging only. *Gate:* ledger reconciles with Alpaca paper.
2. **Deterministic core:** screener, indicators, regime classifier, sizing, full risk gate including the market-shock buying freeze. *Gate:* risk rules pass tests and fault injection.
3. **Claude in shadow mode:** theses (with and without themes) and pivotal-event emergency theses are produced and logged but not traded. *Gate:* schema-valid, citations traceable, stable across reruns.
4. **Autonomous paper trading:** all Claude variant portfolios (FR15) trade on paper with LLM-off and random controls; Claude places the mirrored portfolios' orders; themes and pivotal events act; reflection memory on. Related-names experiment: feed Claude one- and two-step context from the links table and compare decisions with and without it.
5. **Expand scope:** shorts, then defined-risk options (add ORATS), then international ETFs, each with its own attribution.
6. **Live pilot:** when David judges the system is working as expected; small capital, same code path.

The production VM is in place before phase 4 starts, so no daily run is missed.

**Open decisions**

- [ ] Portfolio drawdown limit (after paper results)
- [x] Starting paper capital — every pipeline runs at $5,000 and at $100,000 (FR15.3)
- [x] Postgres vs DuckDB for storage — Postgres
- [ ] Cloud host for production
- [x] Whether to add Tiingo point-in-time fundamentals in phase 1 — deferred (see DR5)
- [ ] Account type for live trading (taxable vs IRA) and its effect on short-term gains and wash-sale handling

**To verify with providers before building on them**

- [x] Whether Alpaca's free market-data plan covers daily bars — no: Basic is IEX-only (research report §3), which understates volume for the liquidity filters, so keep the $99 plan
- [x] Whether Alpaca paper supports multi-leg option orders (needed for phase 5 spreads) — yes: Level 3 multi-leg (order class `mleg`) covers spreads, straddles, strangles, iron condors and butterflies in paper, and live as well ([changelog](https://docs.alpaca.markets/us/changelog/multi-leg-level-3-options-trading-in-paper), [guide](https://docs.alpaca.markets/us/docs/options-level-3-trading), checked 2026-10-11). Limits for the adapter: no stock legs in the same order, every short leg must be covered within the order, leg ratios in simplest form; the guide's examples use only limit, day orders.
