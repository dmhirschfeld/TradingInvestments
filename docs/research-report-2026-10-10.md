# Autonomous Claude-Driven Trading System: Architecture, Evidence, Data, Brokers, and Realistic Expectations

*Research report, October 10, 2026*

**Bottom line: Build it, but build it as a deterministic quant system where Claude Opus 5.5 is one research input. Claude should never be the trader. Expect the honest outcome to be "no statistically provable edge over SPY or a momentum baseline for years," and treat tripling the S&P 500 as an unrealistic target.** The published evidence is consistent. LLM trading agents can turn a profit, but they rarely beat simple baselines once you remove look-ahead bias, lengthen the test, or charge realistic costs. The value you can capture is in reading text at scale (filings, transcripts, news), not in timing or sizing positions.

## TL;DR
- **Architecture:** Claude reads text and writes structured trade theses: direction, conviction, catalysts, and the conditions that would prove the thesis wrong. Deterministic code handles everything else: regime detection, position sizing, risk vetoes, execution, and the audit trail. Run three shadow portfolios on the same rails (SPY, a rules-based momentum strategy, and the same pipeline with the LLM switched off), so you can measure what Claude adds and not just what the market gave you.
- **Evidence:** StockBench found agents "rarely outperform simple baselines." The KDD 2026 FINSABER study (20 years, 100+ symbols) found reported LLM advantages "deteriorate significantly," with LLMs too conservative in bull markets and too aggressive in bear markets. In live arenas, most frontier models lost money. Claude Sonnet 4.5 lost heavily in both Alpha Arena seasons: −42% in Season 1 and −35% at a Season 1.5 snapshot. Any backtest that falls inside the model's training window is contaminated. For Opus 5.5 (knowledge cutoff June 2026), that means only forward testing gives clean evidence.
- **Stack and cost:** Start paper trading on Alpaca (free paper account plus $99/mo Algo Trader Plus for full SIP and OPRA data), run your own internal ledger, and plan to go live on Interactive Brokers. A solid data stack costs about $250–450/mo. Claude API cost for a funnel that sends about 100 candidates a day to deep review runs roughly $100–400/mo with batching and caching. Multi-agent debate on every name multiplies that several times.

---

## Recommendations (decision-ready)

1. **Claude proposes and code disposes.** The LLM never calls an order endpoint directly. Every LLM output is a validated JSON thesis that passes through a deterministic sizing engine and a hard-veto risk gate.
2. **Make the momentum baseline and an "LLM-off" ablation first-class products, not afterthoughts.** If Claude can't beat the identical pipeline running without Claude, after costs, it isn't adding value. That holds no matter how good returns versus SPY look in a bull market.
3. **Don't trust any LLM backtest before July 2026.** Use historical backtests only for the deterministic parts (momentum baseline, risk rules, sizing). Judge the LLM only on forward paper trading. Every model upgrade moves the contamination window forward.
4. **Run your own simulator as the source of truth, and use broker paper accounts only as an execution-realism check.** Alpaca paper does not model borrow fees, dividends, liquidity limits, or locates.
5. **Phase in risk:** long-only US stocks and ETFs first, then shorts, then defined-risk options only (spreads, never naked short options), then international ETFs.
6. **Set a realistic goal.** Aim for SPY-like returns with a smaller drawdown, or a modest excess return (low single digits a year) that survives costs. Treat "3× SPY" as a sign of luck or excess leverage if it ever shows up.
7. **Go-live gate:** require at least 6–12 months of forward paper trading and 100+ closed trades. The system must beat the momentum baseline and the LLM-off ablation on Sharpe after modeled costs, stay inside the drawdown limit, and have no unexplained operational incidents. Then start with a deliberately small live allocation.

---

## Key Findings (summary)

**Architecture**
- The academic frameworks (TradingAgents, FinMem, FinCon, FinAgent, TradingGPT) model trading firms: analyst agents, bull/bear debate, a trader agent, a risk team, and reflection memory. Use them as design references, not as proven alpha.
- LLMs are strongest at unstructured text, event interpretation, and spotting catalysts. They are weak at numeric prediction, timing, and consistent sizing.
- Regime detection, sizing, and risk should be deterministic. FINSABER's central finding is a regime failure, and Alpha Arena's losses were mostly leverage and risk failures.

**Evidence**
- StockBench (March–June 2025, DJIA stocks, contamination-free): agents can be profitable but "rarely outperform simple baselines." The study did not model costs or slippage.
- FINSABER (Li, Kim, Cucuringu & Ma, KDD 2026) found that "previously reported LLM advantages deteriorate significantly under broader cross-section and over a longer-term evaluation." Over 20 years and 100+ symbols, the LLM strategies were "overly conservative in bull markets... and overly aggressive in bear markets, incurring heavy losses."
- LiveTradeBench (50 live days, 21 LLMs): general capability does not predict trading skill (Spearman correlation 0.054 between LMArena score and stock returns), and reasoning models over-adjust.
- Alpha Arena: Season 1 was crypto perpetuals, where 4 of 6 models lost money. Season 1.5 was US stock tokens, won by the Grok 4.20 "Mystery Model." In a December 6 snapshot, Grok 4.20 was the only profitable model (+22.38%), and the other seven ranged from −2.29% (GPT-5.1) to −53.39% (Grok 4). Claude Sonnet 4.5 lost heavily in both seasons.
- Look-ahead bias is measurable and material. The "Profit Mirage" paper found that back-tested returns evaporate after the knowledge cutoff.

**Data (tiers)**
- Free: SEC EDGAR, FRED, Alpaca Basic (IEX feed), Massive Basic, FMP Basic, Tiingo Free.
- Around $100–500/mo: Alpaca Algo Trader Plus $99, FMP Ultimate $149, Benzinga news via Massive $99, Quiver Trader $75.
- $500+/mo: add ORATS ($199–$599), the Unusual Whales API, Massive Advanced tiers, and EODHD for international data.

**Brokers**
- Alpaca is best for building: free paper trading, options and shorting in paper, and an official MCP server.
- Interactive Brokers is best for going live: $1M paper account, the same simulator as its live platforms, global markets, and the most realistic short-selling.
- Tradier is a cheap option for options-heavy trading. The Schwab API has no paper trading.

**Returns**
- According to S&P Dow Jones Indices' SPIVA U.S. Year-End 2025 scorecard, 79% of active large-cap US funds underperformed the S&P 500 in 2025, a year the index rose 18%. That was worse than 2024's 65% rate and the fourth-worst year in SPIVA's 25-year history.
- Proving even a strong edge statistically takes years, not months.

---

## Details

### 1. Architecture: where the LLM sits

**Reference frameworks**
- **[TradingAgents](https://github.com/tauricresearch/tradingagents)** (UCLA/MIT, arXiv 2412.20138):
  - Analyst agents (fundamental, sentiment, news, technical), bull/bear researchers who debate, a trader, a risk-management team, and reflection.
  - Built on LangGraph. Supports Claude 4.x and later.
  - The paper claims better cumulative return, Sharpe, and max drawdown than baselines, but over a short window that is likely contaminated. The repo itself says it is "designed for research purposes."
- **FinMem / TradingGPT:** layered memory (short, medium, and long term), character design, and reflection on past trades. This is the right idea for learning from past trades.
- **FinCon:** a manager–analyst hierarchy with "conceptual verbal reinforcement," meaning lessons written in plain text. FinAgent (KDD 2024) is a multimodal, tool-augmented design.
- **FactFin ("Profit Mirage" paper):** the most important design lesson. It makes the LLM a *strategy generator* that is tested against counterfactuals, not a direct decision-maker, because direct LLM decisions lean on memorized outcomes.
- **[FINSABER](https://github.com/waylonli/FINSABER):** a rigorous backtesting harness built on Backtrader. Use it as a reference for how to evaluate.

**Recommended layered design (each layer is deterministic unless marked LLM)**
1. **Point-in-time data store.** Every record carries an "as-known-at" timestamp, and fundamentals are stored as reported, not restated. Tiingo offers point-in-time as-reported fundamentals.
2. **Feature and screen engine.** Factors (momentum, quality, value, volatility), liquidity filters, and an earnings calendar. This step shrinks a universe of about 3,000+ names to about 50–150 candidates a day.
3. **Regime classifier.** Rules or an HMM over trend (SPY vs. its 200-day average), volatility (VIX level and term structure), credit spreads and the yield curve (FRED), and market breadth. The output is a discrete regime that sets gross/net exposure limits and turns strategy sleeves on or off (momentum, mean-reversion, defensive). Claude may write a regime narrative, but it cannot override the classifier.
4. **Research layer (LLM).** Claude analyzes each candidate's filings, transcript, news, estimate revisions, insider/13F changes, and options context. Use a bull/bear debate only for names that make the shortlist. The required output is JSON: direction, conviction (1–5), horizon, catalyst dates, thesis, conditions that would invalidate the thesis, key risks, and data citations. Reject any output whose numbers can't be traced to the input data.
5. **Portfolio construction.** Map conviction to weight using volatility targeting (inverse-volatility or ATR-based sizing) times a conviction multiplier, capped by fractional Kelly. Hard caps apply: for example, 5% per name, 25% per sector, and regime-dependent gross/net exposure.
6. **Risk gate (hard veto).** Checks for liquidity (percent of average daily volume), max loss per position and per portfolio, stop and invalidation triggers, earnings-blackout rules, defined-risk-only options, borrow availability for shorts, a daily-loss circuit breaker, and a manual kill switch.
7. **Execution adapter.** Limit orders, idempotent order IDs, reconciliation against the broker, and slippage modeling in the internal ledger.
8. **Memory and reflection (LLM, gated).** After each trade closes, Claude writes a post-mortem stored in a retrieval store. A lesson can only change prompts or rules after it recurs across many trades. Single-trade "lessons" are mostly noise and invite overfitting.
9. **Audit log.** Append-only: data-snapshot hashes, full prompts, model ID and version, temperature, raw outputs, parsed theses, risk-gate decisions, orders, and fills.
10. **Evaluation harness.** Shadow portfolios run in parallel: SPY total return, a momentum baseline (for example 12-1 month cross-sectional momentum or ETF dual momentum with a trend filter), the LLM-off pipeline, and a random-entry control with identical sizing and risk.

**Where LLMs add value vs. where to use quant methods**

| Task | Use LLM? | Why |
|---|---|---|
| Reading 10-K/10-Q, 8-K, transcripts, news; spotting catalysts and risks | **Yes** | Its comparative advantage. Scales analyst-hours. |
| Synthesizing a thesis and stating what would invalidate it | **Yes** | Makes decisions auditable and testable. |
| Sanity-checking quant signals | **Yes** | Good at spotting context the numbers miss. |
| Regime detection | Narrative only | The LLM's regime asymmetry is documented. Use statistics. |
| Position sizing, stops, exposure | **No** | LLMs are inconsistent with numbers, and Alpha Arena's losses came from leverage. |
| Price prediction and timing | **No** | No evidence of skill. Reasoning models over-adjust. |
| Execution | **No** | Deterministic code only. |

### 2. Evidence on LLM trading performance

- **StockBench** (Tsinghua/BUPT, arXiv 2510.02209): DJIA stocks over 82 trading days (March 3 to June 30, 2025), with prices, fundamentals, and news. Conclusion: "although current agents can be profitable, they rarely outperform simple baselines." The test ignores costs, slippage, and liquidity, and four months can miss whole regimes.
- **FINSABER** (Li, Kim, Cucuringu, Ma; KDD 2026): backtests over two decades and 100+ symbols show LLM advantages "deteriorate significantly." The paper blames survivorship and data-snooping bias for earlier claims and recommends prioritizing trend detection and regime-aware risk controls over framework complexity.
- **LiveTradeBench** (UIUC, arXiv 2511.03628): 21 LLMs over 50 live days (August 18 to October 24, 2025), 15 US stocks plus Polymarket.
  - Stock returns clustered at +1.8% to +6.3% in a rising market, with no costs modeled.
  - Spearman correlation between LMArena score and stock returns: 0.054.
  - Reasoning models did not confer trading advantages and showed higher volatility.
  - Agents overreacted to attention-grabbing but non-decisive news.
  - Claude Opus 4/4.1 were among the more conservative, low-drawdown models.
- **Alpha Arena (Nof1), real money:**
  - **Season 1** (crypto perpetuals, October 18 to November 3, 2025): final balances from $10,000: Qwen3 Max $12,231, DeepSeek $10,489, Claude Sonnet 4.5 $5,799, Gemini 2.5 Pro $5,445, Grok 4 $4,208, GPT-5 $4,126.
  - **Claude Sonnet 4.5 in Season 1:** −42.01%, attributed partly to high leverage.
  - **Season 1.5** (US stock tokens, November 19 to December 3, 2025): Grok 4.20 ("Mystery Model") won. In a December 6 snapshot it was the only profitable model; Claude Sonnet 4.5 was at −35.08%.
  - **Caveats:** two-week runs with leverage on crypto venues; behavioral evidence, not proof of skill.
- **Contamination and look-ahead research:**
  - Glasserman & Lin: any backtest that includes an LLM's training window is tainted; anonymizing entities helps.
  - "Detecting Lookahead Bias in LLM Forecasts" (arXiv 2512.23847): memorization-driven predictability collapses to near zero right after the training cutoff.
  - "Profit Mirage" (arXiv 2510.07920): most published agents' back-tested returns evaporate once the knowledge window ends.
  - FinCAD (arXiv 2605.24564): memorization is strongest for mega-caps such as NVDA, MSFT, and AAPL.
- **Known failure modes to design against:** leverage blowups, overtrading on headlines, wrong posture for the regime, mega-cap concentration, hallucinated figures, inconsistent answers to identical prompts, prompt sensitivity, silent behavior changes on model updates, survivorship bias, and ignoring costs and borrow fees.

**How to evaluate properly**
- **Forward paper trading is the only clean test of the LLM layer.** Pin the model version and log every upgrade.
- **Point-in-time data and a survivorship-free universe** for any deterministic backtest.
- **Statistical power:** the t-statistic of excess return ≈ information ratio × √years. Reaching t ≈ 2 takes about 16 years at IR 0.5, 4 years at 1.0, and 1 year at 2.0. A few months can falsify a bad system but cannot prove a good one.
- **Correct for multiple testing:** every prompt variant is a new trial. Use the deflated Sharpe ratio and probability of backtest overfitting. Pre-register go-live criteria.
- **Attribute returns:** compare against the LLM-off ablation and the momentum baseline, and run factor regressions (market, size, momentum, quality).

### 3. Data: what's needed and who to buy it from

**Priority order for swing-to-months decisions:**
1. Clean adjusted daily prices and volume, plus intraday data for execution.
2. Fundamentals and estimate revisions.
3. Earnings dates and transcripts.
4. SEC filings (8-K, 10-Q/K, Form 4).
5. News.
6. Macro and regime inputs.
7. Options IV, skew, and term structure.
8. Insider and 13F flows.
9. Unusual options activity and alternative data (lowest signal-to-cost; add last).

**Provider comparison (prices as published; verify at signup)**

| Need | Provider | Price | Notes |
|---|---|---|---|
| Macro | [FRED](https://fred.stlouisfed.org/) | Free | Yield curve, credit spreads, claims, etc. |
| Filings, Form 4, 13F | [SEC EDGAR](https://www.sec.gov/edgar/search/) | Free | Primary source. Needs parsing work. |
| Prices, stocks + options | [Alpaca Market Data](https://docs.alpaca.markets/us/docs/about-market-data-api) | Basic free (IEX only); **Algo Trader Plus $99/mo** (SIP + OPRA) | Indicative feed not for live trading. |
| Prices, deep history | [Massive (formerly Polygon.io)](https://massive.com/pricing) | Stocks Basic $0; Stocks Advanced $199/mo; [Options](https://massive.com/options) $29 / $79 / $199 | Options Developer and up include Greeks and IV. |
| News + analyst ratings | [Benzinga via Massive](https://massive.com/partners/benzinga) | $99/mo per dataset | History back to 2009. |
| Fundamentals, transcripts, 13F | [Financial Modeling Prep](https://site.financialmodelingprep.com/pricing-plans) | Basic free; Starter ~$22, Premium ~$59, **Ultimate ~$149/mo** | Transcripts, 13F, global need Ultimate. Check checkout price. |
| Fundamentals (point-in-time) | [Tiingo](https://www.tiingo.com/products/fundamental-data-api) | Free tier; Power $30/mo; fundamentals add-on $9.99–$49.99/mo | As-reported point-in-time data. |
| International EOD + fundamentals | [EODHD](https://eodhd.com/pricing) | $19.99 / $29.99 / $59.99 / $99.99 All-in-One | 60–70+ exchanges. |
| Insider, congressional, alt data | [Quiver Quantitative](https://api.quiverquant.com/pricing/) | Hobbyist $30/mo; **Trader $75/mo** | No commercial rights on personal tiers. |
| Options flow, GEX, dark pool | [Unusual Whales API](https://unusualwhales.com/public-api) | ~$150–375/mo | Official MCP server. Signal value unproven. |
| IV surfaces | [ORATS Data API](https://orats.com/data-api) | $199 / $299 / $599 / $899 per month | Trust ORATS's own page. |

**Tiered budgets**
- **Free / low (<$100/mo):** Alpaca Basic, EDGAR, FRED, FMP Basic or Starter, Tiingo Free or Power, Massive Basic. Enough to build the pipeline and run long-only stocks and ETFs; not enough for options.
- **~$100–500/mo (recommended for paper phase), about $420/mo:** Alpaca Algo Trader Plus $99, FMP Ultimate $149, Benzinga via Massive $99, Quiver Trader $75, plus free EDGAR and FRED.
- **$500+/mo (only after an edge shows):** ORATS, Unusual Whales API, Massive Advanced tiers, EODHD All-in-One.

**Claude API costs**
- Opus 5.5: $4 / $20 per million input/output tokens; Batch $2 / $10; cache reads $0.20/M. Sonnet 5.5: $2 / $10. Haiku 4.5: $1 / $5.
- A deep single-ticker analysis (~30K input + ~3K output) costs ~$0.18 standard, ~$0.09 batched.

| Design | Daily LLM work | Approx. monthly cost |
|---|---|---|
| Focused: 25 deep reviews/day + 1 portfolio review | ~26 calls | ~$50–100 |
| Funnel: 100 deep reviews/day + Haiku triage on ~1,000 headlines | ~100 Opus + cheap triage | ~$150–400 |
| TradingAgents-style debate (~8–12 calls/ticker) on 100 names/day | ~1,000 calls | ~$1,500–4,000 |

### 4. Brokers and paper-trading fidelity

| Broker | Paper trading | Options / shorting | Cost (live) | Fidelity caveats | Role |
|---|---|---|---|---|---|
| [Alpaca](https://docs.alpaca.markets/us/docs/paper-trading) | Free, $100K default, up to 3 accounts | Options and shorting in paper | Commission-free stocks | NBBO fills with no liquidity check; no dividends, borrow fees, margin interest or locates in paper | **Build and paper phase** |
| [Interactive Brokers](https://www.interactivebrokers.com/en/pricing/commissions-home.php) | $1M paper; same simulator as live | Full options, real borrow/locate, 135+ markets | $0.005/share (min $1); options $0.65/contract | Clunky TWS/Gateway sessions | **Live phase, international, shorting** |
| [Tradier](https://tradier.com/individuals/pricing) | Sandbox (delayed data) | Options-first; multi-leg | Pro $10/mo; Lite $0.35/contract | Sandbox lacks account activity | Options-heavy alternative |
| [Schwab Trader API](https://developer.schwab.com/products/trader-api--individual) | No paper trading | Options and short selling | Free API | Live only | Skip for now |

### 5. Phased build plan and stack

- **Phase 0, Foundations:** point-in-time data store, broker adapter, internal ledger, audit log, SPY and momentum shadow portfolios. *Gate:* ledger reconciles with Alpaca paper.
- **Phase 1, Deterministic core:** screener, regime classifier, sizing, risk gate; momentum baseline trades on paper. *Gate:* risk rules pass tests and fault injection.
- **Phase 2, LLM in shadow mode:** theses logged, not traded. *Gate:* schema validity, traceable numbers, stable reruns.
- **Phase 3, Autonomous paper trading:** LLM-weighted portfolio, LLM-off ablation, random control; debate and reflection memory.
- **Phase 4, Expand scope:** shorts, defined-risk options, international ETFs, each with attribution.
- **Phase 5, Live pilot:** after the go-live gate; small capital, same code path, kill switch.

**Stack:** Python 3.12 + uv, Anthropic SDK / Agent SDK, optional LangGraph, Postgres or DuckDB + Parquet, vectorbt / Backtrader / LEAN, Prefect, Streamlit or Grafana, cloud VM for production. MCP servers ([Alpaca](https://github.com/alpacahq/alpaca-mcp-server), Unusual Whales, FMP) for interactive research only, never in the production loop.

### 6. Realistic return expectations

- **Tripling the S&P 500 is not achievable as a design target.** Short-run results like that usually mean leverage, sector concentration, or luck.
- **Base rates:** 79% of active large-cap US funds underperformed the S&P 500 in 2025; only 4.5% of above-median funds stayed above median vs. 6.25% expected by chance.
- **No study shows durable, cost-adjusted LLM alpha.**
- **Plausible outcomes, most to least likely:** (1) returns similar to SPY or momentum with no detectable LLM value; (2) similar returns with lower drawdown from the risk and regime layer; (3) modest low-single-digit excess return from text-driven selection, taking years to confirm; (4) large underperformance from overtrading or regime errors.

## Caveats
- Several sources are third-party: Alpha Arena results, Unusual Whales pricing, Schwab API capabilities, and Opus 5.5 pricing. Confirm prices at signup.
- No published benchmark has tested Claude Opus 5.5 specifically.
- Cost estimates are illustrative token budgets, not measured usage.
- Not investment advice. Live autonomous trading carries regulatory and tax considerations (wash sales, short-term gains, pattern-day-trader rules).

## Post-report decisions (recorded in the requirements doc)
- Language: Python.
- Universe expanded to small caps; IWM added as a benchmark; 8–15 positions, 10–15% per-name cap; options sleeve 10–20%, defined-risk only.
- Relationships stored in a dated Postgres links table from phase 1; no separate graph database unless traversal queries become deep or slow.
