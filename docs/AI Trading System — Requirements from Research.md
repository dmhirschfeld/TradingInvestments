# AI Trading System — Requirements

Oct 10, 2026 · @David Hirschfeld

## Summary

Build a Python system that paper-trades US stocks, ETFs and defined-risk options on its own, using Claude Opus 5.5 for research and deterministic code for every trading decision. Holding periods run from about one week to several months; no day trading.

- **Core principle:** Claude proposes, code disposes. The model writes structured trade theses; sizing, risk vetoes and order placement are code. The model never has direct access to placing orders.
- **Phase 1 scope:** simulated portfolio only (Alpaca paper plus an internal ledger). Real money only after the go-live gate passes.
- **Success:** beat SPY and IWM on risk-adjusted return after costs, and beat the same pipeline with Claude turned off. Tripling the benchmark is upside, not the target.
- **Build:** executed with GSD-T.

## Goals, non-goals and metrics

The system must prove Claude adds measurable value over cheap baselines before any real money is used.

**Goals**

- G1. Trade autonomously on paper across large, mid and small caps, ETFs, and defined-risk options.
- G2. Switch strategy posture with market regime (trend, volatility, credit conditions).
- G3. Log every decision so any trade can be explained and replayed.
- G4. Measure Claude's contribution against shadow portfolios that run the same rules without it.

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

Metrics tracked daily for every portfolio: total return, excess return, Sharpe, Sortino, max drawdown, volatility, hit rate, average win/loss, turnover, and costs paid.

## Architecture

A daily pipeline runs after the US close; Claude appears in three steps, and every step that touches money is code.

&#91;embedded content: daily pipeline · 12 components, Claude in 3\]

Claude's theses feed sizing, never the broker directly. The regime classifier also sets the risk gate's exposure limits, and the ledger feeds both evaluation and Claude's post-trade reflection.

## Functional requirements

Each component has one owner of truth; only the execution adapter talks to the broker.

**FR1 Data store**

- FR1.1 Store every record with an as-known-at timestamp; queries return only what was known at the decision time.
- FR1.2 Store fundamentals as reported, never restated; keep delisted symbols.
- FR1.3 Ingest on a schedule after the US close, with retries and data-quality checks (gaps, stale prices, splits).
- FR1.4 Store relationships in one Postgres links table: from-entity, to-entity, link type, valid-from, valid-to, known-at, source. It covers companies, funds, insiders, news, sectors and macro factors under the same point-in-time rule.
- FR1.5 No separate graph database. Add graph queries ([Apache AGE](https://age.apache.org/)) only if traversal queries become deep or slow; [Neo4j](https://neo4j.com/) is the last resort.

**FR2 Screener**

- FR2.1 Reduce a universe of large, mid and small caps plus ETFs to 50–150 daily candidates.
- FR2.2 Factors: momentum, quality, value, volatility; filters on minimum price, average dollar volume and spread.
- FR2.3 Always include current holdings for re-review.

**FR3 Regime classifier**

- FR3.1 Classify the market into discrete regimes from trend (SPY vs 200-day average), VIX level and term structure, credit spreads, yield curve and breadth.
- FR3.2 Each regime sets gross/net exposure limits and which strategy sleeves are active.
- FR3.3 Claude may write a regime narrative but cannot change the classification.

**FR4 Triage (Haiku or Sonnet)**

- FR4.1 Scan news and new filings for each candidate and cut to a shortlist for deep review.

**FR5 Deep research (Opus 5.5)**

- FR5.1 Run a bull/bear analysis per shortlisted name and per open position.
- FR5.2 Output validated JSON: ticker, direction, conviction 1–5, horizon, instrument (stock or option structure), catalysts with dates, thesis, invalidation conditions, key risks, data citations.
- FR5.3 Reject any output that fails the schema or cites numbers not in the input data.
- FR5.4 Pin the model version and temperature; log both on every call.
- FR5.5 Use the Batch API and prompt caching where latency allows.

**FR6 Portfolio construction**

- FR6.1 Size by volatility target × conviction multiplier, capped by fractional Kelly.
- FR6.2 Target 8–15 positions; per-name cap 10–15%; per-sector cap 25–30%.
- FR6.3 Options sleeve capped at 10–20% of equity, defined-risk structures only.

**FR7 Risk gate** (see Risk management)

**FR8 Execution**

- FR8.1 Place limit orders through the broker adapter with idempotent client order IDs.
- FR8.2 Reconcile broker positions against the internal ledger daily; halt on mismatch.
- FR8.3 Broker adapter is an interface: Alpaca paper first, Interactive Brokers later.

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

- FR12.1 Run all shadow portfolios daily on the same data.
- FR12.2 Dashboard shows equity curves, metrics, open positions with theses, and attribution.
- FR12.3 Alerts (Slack or email) for fills, risk-gate vetoes, circuit breakers and job failures.

## Data requirements

The recommended paper-phase stack costs about $420/mo for data plus roughly $150–400/mo for the Claude API. Prices are from the October 2026 research report; confirm at signup.

| Data | Provider | Price/mo | Phase |
| --- | --- | --- | --- |
| Stock + options prices (SIP, OPRA) | [Alpaca Algo Trader Plus](https://docs.alpaca.markets/us/docs/about-market-data-api) | $99 | 1 |
| Fundamentals, transcripts, 13F | [Financial Modeling Prep Ultimate](https://site.financialmodelingprep.com/pricing-plans) | \~$149 | 1 |
| News and analyst ratings | [Benzinga via Massive](https://massive.com/partners/benzinga) | $99 | 1 |
| Insider and congressional trades | [Quiver Quantitative Trader](https://api.quiverquant.com/pricing/) | $75 | 1 |
| Filings, Form 4, 13F (primary) | [SEC EDGAR](https://www.sec.gov/edgar/search/) | Free | 1 |
| Macro and regime inputs | [FRED](https://fred.stlouisfed.org/) | Free | 1 |
| Point-in-time fundamentals | [Tiingo](https://www.tiingo.com/products/fundamental-data-api) | $30–80 | 1 (optional) |
| Implied volatility surfaces | [ORATS](https://orats.com/data-api) | $199–599 | 4 (options sleeve) |
| Options flow | [Unusual Whales API](https://unusualwhales.com/public-api) | \~$150–375 | Later, only if it proves useful |
| International data | [EODHD](https://eodhd.com/pricing) | $99.99 | Later |

- DR1. Each provider sits behind an adapter so it can be swapped without touching strategy code.
- DR2. Raw responses are stored before parsing, so data can be reprocessed.
- DR3. Survivorship-free history (including delisted names) is required for any deterministic backtest.

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
| Portfolio drawdown limit | To be set after paper trading (open decision) |
| Kill switch | Manual, closes or freezes all activity |

- RM1. The gate logs every veto with the rule that fired.
- RM2. Gross and net exposure limits come from the regime classifier.
- RM3. Any data-quality failure or ledger mismatch blocks trading for that day.

## Evaluation and go-live gate

Claude is judged only on forward paper trading, because any backtest before its June 2026 knowledge cutoff is contaminated.

- EV1. Historical backtests are allowed only for deterministic parts: momentum baseline, regime classifier, sizing and risk rules.
- EV2. Every prompt or model change is logged as a new trial; results use the deflated Sharpe ratio to correct for multiple testing.
- EV3. Factor regression (market, size, momentum, quality) runs monthly to separate skill from beta and style tilts.
- EV4. Go-live criteria are written down before paper trading starts and not changed afterward.

**Go-live gate (all must pass)**

- [ ] At least 6–12 months of forward paper trading and 100+ closed trades
- [ ] Beats SPY and IWM on Sharpe after modeled costs
- [ ] Beats the momentum baseline and the LLM-off pipeline on Sharpe after costs
- [ ] Max drawdown within the limit set after paper trading
- [ ] No unexplained operational incidents in the last 3 months
- [ ] First live allocation is a deliberately small amount

## Non-functional requirements and stack

The system is Python end to end, developed on Mac and run in production on a small cloud VM so it never misses a run because a laptop is asleep.

| Area | Choice |
| --- | --- |
| Language and packaging | Python 3.12, uv |
| Claude access | Anthropic Python SDK (structured outputs, Batch API, prompt caching) |
| Agent orchestration | Plain Python first; LangGraph only if the debate flow needs it |
| Storage | Postgres (or DuckDB + Parquet) for point-in-time data, ledger and audit log |
| Analytics | pandas, statsmodels, hmmlearn; vectorbt for baseline backtests |
| Scheduling | Prefect |
| Broker | [Alpaca](https://docs.alpaca.markets/us/docs/paper-trading) paper; [Interactive Brokers](https://www.interactivebrokers.com/en/pricing/commissions-home.php) for live |
| Dashboard and alerts | Streamlit; Slack or email alerts |
| Dev tooling | [Alpaca MCP server](https://github.com/alpacahq/alpaca-mcp-server) for interactive research in Claude Code only, never in the production loop |

- NF1. Secrets in a secrets manager or environment, never in code or logs.
- NF2. Every daily run is idempotent and restartable from the last completed step.
- NF3. Same code path for paper and live; only the broker adapter and config change.
- NF4. Test coverage required on sizing, risk gate, ledger and broker adapter, including fault injection.
- NF5. Monthly Claude API spend is capped with an alert at 80% of budget.

## Phases and open decisions

Each phase ends at a gate, not a date.

1. **Foundations:** data store (including the links table), broker adapter, internal ledger, audit log, SPY/IWM/momentum shadow portfolios. *Gate:* ledger reconciles with Alpaca paper.
2. **Deterministic core:** screener, regime classifier, sizing, risk gate; momentum baseline trades on paper. *Gate:* risk rules pass tests and fault injection.
3. **Claude in shadow mode:** theses are produced and logged but not traded. *Gate:* schema-valid, citations traceable, stable across reruns.
4. **Autonomous paper trading:** Claude-weighted portfolio live on paper with LLM-off and random controls; reflection memory on. Related-names experiment: feed Claude one- and two-step context from the links table and compare decisions with and without it.
5. **Expand scope:** shorts, then defined-risk options (add ORATS), then international ETFs, each with its own attribution.
6. **Live pilot:** only after the go-live gate passes; small capital, same code path.

**Open decisions**

- [ ] Portfolio drawdown limit (after paper results)
- [ ] Starting paper capital (Alpaca default is $100K)
- [ ] Postgres vs DuckDB for storage
- [ ] Cloud host for production
- [ ] Whether to add Tiingo point-in-time fundamentals in phase 1
- [ ] Account type for live trading (taxable vs IRA) and its effect on short-term gains and wash-sale handling
