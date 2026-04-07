# FINTECH 543 Final Project

## Four-Week Weighted Momentum Strategy (S&P 500 Dynamic Universe)

This repository documents and implements a short-horizon quantitative strategy for the final project.

The strategy is a four-week weighted cross-sectional momentum model on S&P 500 constituents, with dynamic membership control to avoid survivorship bias, Yahoo Finance price data, weekly rebalancing, and weekly performance reporting.

## 1. Project Objective

The objective is to test whether short-horizon cross-sectional momentum can generate stable excess return versus a benchmark under realistic trading frictions and explicit risk controls.

Primary goals:
- Outperform SPY on excess return and information ratio.
- Keep portfolio risk within a defined annualized volatility target.
- Maintain a transparent and reproducible workflow suitable for final presentation.

## 2. Requirement Mapping

- Capital: USD 50,000,000 initial capital.
- Portfolio breadth: at least 10 unique securities at each rebalance.
- Short borrowing cost: annualized 10% borrowing cost on short exposure, accrued daily.
- Unique quantitative strategy: cross-sectional momentum with EWMA weighting and dynamic universe handling.
- Defined benchmark and risk target: benchmark is SPY; risk target is explicit annualized volatility.
- Short-term construction: designed for a four-week horizon with weekly rebalancing.
- Minimum run window before presentation: at least 4 full trading weeks of tracked model performance.
- Submission readiness: code, documentation, and weekly reports prepared for hand-in and presentation.

## 3. Data Policy

All price and benchmark series are sourced from Yahoo Finance.

Data components:
- Asset prices: daily open and close from Yahoo Finance.
- Benchmark prices: SPY from Yahoo Finance.
- Universe metadata: historical S&P 500 membership intervals used only to define tradable sets by date.

Important note on survivorship bias:
- We do not backtest on current constituents only.
- We trade only securities that were active members on each signal date.

## 4. Signal Definition (EWMA Momentum)

Professor guidance requires recent observations to receive higher weight. We therefore use EWMA-based momentum.

For each stock i on signal date t:

1) Compute daily close-to-close return:

$$
r_{i,t} = \frac{C_{i,t}}{C_{i,t-1}} - 1
$$

2) Compute EWMA momentum score over recent returns:

$$
Score_{i,t} = \sum_{k=0}^{K-1} w_k\, r_{i,t-k}, \quad w_k = (1-\lambda)\lambda^k, \quad \sum_k w_k = 1
$$

Equivalent implementation can use pandas ewm with a selected halflife or span.

Rationale:
- Recent information has stronger predictive value in short-horizon strategies.
- EWMA is simple, robust, and easy to explain.

Current implementation choice:
- We run the production strategy with EWMA as the primary signal method.
- In code this corresponds to:
	- `MOMENTUM_METHOD = "ewma"`
	- `MOMENTUM_SCORE_MODE = "raw"`
	- `EWMA_HALFLIFE_DAYS = 3`

## 5. Stock Selection and Portfolio Construction

On each weekly signal date:
- Filter to tradable stocks in dynamic S&P 500 membership.
- Rank stocks by EWMA momentum score.
- Go long top N and short bottom N (for example 15/15).
- Enforce minimum total unique positions >= 10.
- Use equal weights within long and short sleeves.

Current weighting setup:
- Long sleeve total weight: +100%
- Short sleeve total weight: 0%
- Portfolio size target: top 15 names at each rebalance
- This is the current return-first configuration while keeping the weighted (EWMA) signal requirement.

## 6. Trading Rules

- Signal time: weekly close (end of week).
- Execution time: next trading day open.
- Holding period: until next weekly rebalance.
- Rebalance rule: full refresh of ranks and target weights at each cycle.

Stop-loss policy (adopted in production):
- Type: fixed single-name stop-loss.
- Threshold: 8% from each position's entry reference.
- Scope: long sleeve positions.
- Trigger behavior: if the threshold is breached, the position is exited from the next trading day and remains out until the next scheduled rebalance rebuilds target weights.
- Live rollout date: 2026-03-30.

Rollout convention:
- Live operations: stop-loss is active from the rollout date forward only, so historical live records before rollout remain unchanged.
- Historical research reports (yearly package): can be recomputed under full-history stop-loss for analytical comparison and documentation.

Cost model:
- Transaction cost: no rebalancing fee (set to 0 bps).
- Borrow cost for shorts:

$$
BorrowCost_t = ShortExposure_t \times \frac{0.10}{252}
$$

Net return definition:

$$
r^{net}_t = r^{gross}_t - Cost^{trade}_t - Cost^{borrow}_t
$$

Excess return versus benchmark:

$$
r^{excess}_t = r^{net}_t - r^{SPY}_t
$$

## 7. Backtest Integrity Standards

To keep the backtest academically defensible:
- No look-ahead: only information available at signal time is used.
- No survivorship bias: dynamic historical membership is enforced.
- Realistic timing: close-generated signals, next-open execution.
- Friction-aware: transaction and borrow costs included.
- Reproducibility: fixed data schema, fixed parameter records, deterministic outputs.

Survivorship-bias control in this repository:
- Historical index snapshots are converted to membership intervals (`ticker`, `start_date`, `end_date`).
- On each signal date, the strategy only ranks and trades stocks that were active constituents on that date.
- This logic is implemented in `src/prepare_universe_membership.py` and `src/universe.py`.

## 8. Weekly Report (Required Every Weekend)

Each weekend, produce one performance report with the following sections:

1) Executive Summary
- Weekly return, cumulative return, weekly excess return vs SPY.
- Main drivers and notable risks.

2) Performance Dashboard
- Cumulative return, annualized return, annualized volatility, Sharpe, max drawdown.
- Tracking error and information ratio.

3) Portfolio Diagnostics
- Number of long and short positions.
- Gross exposure, net exposure, turnover.
- Trading cost and borrow cost contribution.

4) Risk and Exceptions
- Breaches of constraints (if any).
- Data quality issues or abnormal moves.

5) Next-Week Plan
- Parameter changes (if any).
- Additional robustness checks.

## 9. Run Plan and Timeline

Target model start date: next Monday.

Execution checklist before launch:
- Freeze current strategy parameters (listed below).
- Confirm dynamic membership file coverage.
- Dry-run full pipeline and validate outputs.

Current frozen parameter set:
- Initial capital: 50,000,000
- Rebalance weekday: Friday (`REBALANCE_WEEKDAY = 4`)
- Signal: EWMA momentum, raw score, halflife = 3
- Selection size: `N_LONG = 15`, `N_SHORT = 0`
- Book weights: long 100%, short 0%
- Stop-loss: fixed 8% single-name stop (`ENABLE_FIXED_POSITION_STOP = True`, `FIXED_POSITION_STOP_PCT = 0.08`, `STOP_LIVE_EFFECTIVE_DATE = "2026-03-30"`)
- Risk target: 18% annualized
- Max gross leverage cap: 2.0
- Minimum signal price filter: 5.0
- Universe control: dynamic historical S&P 500 membership intervals

## 10. Repository Structure

- README.md: project proposal, methodology, and operating plan.
- run_baseline.py: main strategy run script.
- run_experiments.py: parameter sweeps and robustness experiments.
- src/: strategy modules (data, signals, backtest, metrics, plotting, universe).
- data/: input files including membership and optional ticker lists.
- outputs/: generated backtest and report artifacts.

## 11. Suggested Next Steps

1) Freeze parameter set v1 (EWMA + portfolio + risk targets).
2) Start weekly production run next Monday.
3) Archive each weekly report for presentation evidence.
4) Build final slides directly from weekly report history.

## 12. Daily Simulation Operations (4+ Weeks)

Starting tomorrow, run the simulation once per day after market close.

Daily command:

```
python run_daily_simulation.py
```

By default, this command now refreshes `data/prices.csv` from Yahoo incrementally (up to the latest market date), then runs the strategy on the newest available data.
It also refreshes the S&P 500 membership snapshot daily and rebuilds `data/universe_membership.csv` so membership coverage advances with the latest run date.

Optional flags:

```
python run_daily_simulation.py --ticker-source membership
python run_daily_simulation.py --ticker-source sp500
python run_daily_simulation.py --no-refresh-data
python run_daily_simulation.py --no-refresh-membership
python run_daily_simulation.py --strict-membership
```

`--strict-membership` enables fail-fast mode for survivorship-bias control. If `data/universe_membership.csv` is missing or does not cover the latest market date, the run will stop with an error instead of silently falling back.

Weekly forced report command (optional on any day):

```
python run_daily_simulation.py --force-weekly-report
```

### What the daily run updates

- `outputs/baseline_daily_results.csv`: full backtest time series refresh
- `outputs/baseline_summary.csv`: summary metrics refresh
- `outputs/simulation/daily_log.csv`: one row per date with key PnL and exposure fields
- `outputs/simulation/latest_positions.csv`: latest holdings and weights snapshot
- `outputs/simulation/latest_trades.csv`: latest day trade actions vs previous day (BUY/SELL/INCREASE/DECREASE)
- `outputs/simulation/trades_history.csv`: permanent accumulated trade actions by date and ticker
- `outputs/simulation/positions_history.csv`: permanent accumulated end-of-day target positions by date and ticker
- `outputs/simulation/portfolio_value_live.png`: permanent live simulation equity curve from `daily_log.csv`
- `outputs/simulation/data_quality_log.csv`: daily data quality and survivorship-bias status (membership coverage, stale days, fallback flag)
- `outputs/simulation/weekly_reports/weekly_report_YYYY-MM-DD.md`: auto-generated on Fridays

### Fields tracked each day

- Date and run timestamp
- Portfolio value and NAV
- Daily portfolio return, benchmark return, excess return
- Turnover, trading cost, short borrow cost
- Gross and net exposure
- Number of long and short positions
- Rebalance-day flag and signal date
- Long/short ticker lists and serialized weights

### Weekly review checklist

1) Compare weekly portfolio return vs benchmark return
2) Review turnover and exposure stability
3) Review drawdown progression and risk target gap
4) Inspect position concentration from `latest_positions.csv`
5) Write action items for next week in the generated weekly report

## 13. Windows Task Scheduler Automation

You can automate the daily run on Windows with the provided scripts.

Note: the register script creates a launcher file at `C:\Users\<YourUser>\fintech543_daily_simulation.cmd` and schedules that launcher. This avoids Task Scheduler path parsing issues when the project path contains spaces.

Register task (weekdays at 17:30):

```
powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1
```

Register task with custom time:

```
powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1 -RunTime 18:00 -Force
```

Dry run without creating task:

```
powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1 -DryRun
```

Remove scheduled task:

```
powershell -ExecutionPolicy Bypass -File scripts/unregister_daily_task.ps1
```

The unregister script also removes the launcher file created in your user profile.

Execution logs from scheduled runs are saved to:

- `outputs/simulation/task_logs/`
