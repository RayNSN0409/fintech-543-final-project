# FINTECH 543 Final Project
# Model & Strategy Overview (Chinese + English)

## 0) Document Purpose / 文档目的

### 中文
本文件用于完整说明本项目的模型与策略设计、理论依据、回测框架、参数测试、风险控制、幸存者偏差处理、日常运营流程以及当前结果表现。它面向课程提交、周报复盘和课堂展示。

### English
This document provides a complete overview of the project model and strategy, including theoretical rationale, backtesting framework, parameter testing, risk controls, survivorship-bias handling, daily operations, and current performance. It is intended for course submission, weekly review, and presentation.

---

## 1) Strategy Objective / 策略目标

### 中文
我们构建了一个短周期横截面动量策略，目标是在可控风险下获得相对基准（SPY）的超额收益，并通过自动化流程实现“可复现、可追踪、可审计”的研究与模拟交易体系。

核心目标：
- 在 50M 初始资金下运行可执行的策略流程。
- 保持持仓分散（不少于最小持仓数量要求）。
- 按日记录交易与表现，按周生成复盘报告。
- 明确控制并披露数据偏差（特别是幸存者偏差）。

### English
We implement a short-horizon cross-sectional momentum strategy aiming to generate excess returns over SPY under controlled risk. The system is designed to be reproducible, traceable, and auditable through a fully automated simulation workflow.

Core objectives:
- Operate with 50M initial capital under executable rules.
- Maintain diversified holdings (above minimum position requirement).
- Record daily operations and generate weekly review reports.
- Explicitly control and disclose data biases (especially survivorship bias).

---

## 2) Theoretical References / 理论参照

### 中文
本策略主要参考以下经典思想：
- 横截面动量（Cross-sectional Momentum）：按同一时点不同股票近期表现排序，做多强势、做空弱势（当前生产配置为 long-only）。
- 指数加权动量（EWMA）：近期收益赋予更高权重，适配短周期策略。
- 风险目标化（Volatility Targeting）：根据历史实现波动调整仓位规模，使组合风险接近目标区间。
- 相对收益评估（Benchmark-relative Evaluation）：以 SPY 为基准计算超额收益、跟踪误差、信息比率。

常见学术脉络包括：
- Jegadeesh & Titman (1993) 的动量效应研究
- Asness 等关于动量与风格因子的研究
- 风险管理中的目标波动/杠杆约束思想

### English
The strategy follows established concepts:
- Cross-sectional momentum: rank stocks by recent performance and go long winners / short losers (current production setup is long-only).
- EWMA momentum weighting: gives more weight to recent information, suitable for short horizons.
- Volatility targeting: scale exposures based on realized volatility to align with a risk target.
- Benchmark-relative evaluation: use SPY for excess return, tracking error, and information ratio.

The framework is aligned with common academic foundations such as:
- Jegadeesh & Titman (1993) momentum evidence
- Asness et al. momentum/factor literature
- Risk-targeting and leverage-cap principles in portfolio risk management

---

## 3) Full Model Logic / 完整模型逻辑

### 3.1 Data Layer / 数据层

#### 中文
- 价格数据：Yahoo Finance，按日增量更新。
- 成分数据：S&P 500 成分快照 + 区间化 membership 文件。
- 每日流程会先更新成分覆盖，再更新价格数据，确保最新日期可用。

#### English
- Price data: Yahoo Finance with daily incremental refresh.
- Universe data: S&P 500 snapshots transformed into membership intervals.
- Daily pipeline refreshes membership first, then price data to keep coverage current.

### 3.2 Signal Layer / 信号层

#### 中文
- 以个股日收益为基础构建 EWMA 动量分数。
- 支持 raw / risk-adjusted 分数模式（当前生产配置为 raw）。
- 只在调仓频率对应的信号日评估排名。

#### English
- Daily returns are transformed into EWMA momentum scores.
- Both raw and risk-adjusted modes are supported (raw in production).
- Ranking is evaluated on scheduled rebalance signal dates.

### 3.3 Portfolio Construction / 组合构建

#### 中文
- 默认 long-only：取动量排名前 N（当前 N=15）。
- 最少持仓数量约束：若不足阈值则不生成目标仓位。
- 可选 long/short 双边配置（当前 short=0）。

#### English
- Default long-only setup: top N momentum names (currently N=15).
- Minimum position constraint: skip target generation if threshold is not met.
- Long/short construction is supported but current short weight is zero.

### 3.4 Execution & PnL / 执行与收益计算

#### 中文
- 调仓频率：周频（当前按周五信号，下一交易日执行）。
- 日收益：持仓权重与对应标的收益加权。
- 净收益：
  - net_return = gross_return - trading_cost - short_borrow_cost
- 记录组合收益、基准收益、超额收益。

#### English
- Rebalance frequency: weekly (Friday signal, next trading day execution).
- Daily portfolio return: weighted sum of instrument returns.
- Net return:
  - net_return = gross_return - trading_cost - short_borrow_cost
- Portfolio, benchmark, and excess returns are recorded.

### 3.5 Risk Control / 风险控制

#### 中文
- 目标年化波动：18%
- 风险缩放：依据历史实现波动对目标仓位进行缩放。
- 杠杆上限：总暴露不超过上限（当前 2.0）。

#### English
- Target annualized volatility: 18%
- Risk scaling: target weights are scaled by realized volatility.
- Leverage cap: gross exposure constrained by max leverage (currently 2.0).

---

## 4) Backtesting Framework / 回测框架

### 中文
回测包含三层：
1) 基线回测（baseline）：输出标准绩效指标与曲线。
2) 参数扫描（sweep）：在多个参数组合下测试收益/风险特征。
3) 日常滚动模拟（daily simulation）：按真实时间推进，持续写入日志与持仓历史。

输出文件：
- outputs/baseline_daily_results.csv
- outputs/baseline_summary.csv
- outputs/baseline_portfolio_value.png
- outputs/quick_param_sweep*.csv
- outputs/return_max_sweep.csv
- outputs/simulation/*

### English
Backtesting is organized into three layers:
1) Baseline backtest: standard metrics and equity curve.
2) Parameter sweeps: test multiple parameter combinations.
3) Daily rolling simulation: live-like operation with persistent logs and histories.

Main artifacts:
- outputs/baseline_daily_results.csv
- outputs/baseline_summary.csv
- outputs/baseline_portfolio_value.png
- outputs/quick_param_sweep*.csv
- outputs/return_max_sweep.csv
- outputs/simulation/*

---

## 5) What We Tested / 做过哪些测试

### 中文
已完成多轮参数扫描，覆盖：
- EWMA 半衰期
- 持仓数量
- long/short 权重
- 目标波动与杠杆上限
- simple vs ewma 动量方案
- return-first 配置

测试文件包括：
- quick_param_sweep.csv
- quick_param_sweep_v2.csv
- quick_param_sweep_v3.csv
- quick_param_sweep_v4.csv
- quick_param_sweep_return_first.csv
- quick_param_sweep_return_first_focus.csv
- quick_param_sweep_ewma_return_first.csv
- return_max_sweep.csv

### English
Multiple rounds of parameter testing were completed, including:
- EWMA halflife
- Number of holdings
- Long/short book weights
- Volatility target and leverage cap
- Simple vs EWMA momentum
- Return-first configurations

Test files:
- quick_param_sweep.csv
- quick_param_sweep_v2.csv
- quick_param_sweep_v3.csv
- quick_param_sweep_v4.csv
- quick_param_sweep_return_first.csv
- quick_param_sweep_return_first_focus.csv
- quick_param_sweep_ewma_return_first.csv
- return_max_sweep.csv

---

## 6) Evaluation Standards / 评判标准

### 中文
我们采用“绝对收益 + 相对收益 + 风险 + 可执行性”四维评估：
- 绝对收益：total_return, annualized_return, total_pnl
- 相对收益：benchmark_return, excess_return, information_ratio
- 风险控制：annualized_volatility, risk_target_gap, max_drawdown
- 可执行性：turnover, gross/net exposure, unique_positions

### English
Evaluation uses four dimensions: absolute return, relative return, risk, and implementability.
- Absolute return: total_return, annualized_return, total_pnl
- Relative return: benchmark return, excess return, information ratio
- Risk control: annualized volatility, risk_target_gap, max drawdown
- Implementability: turnover, gross/net exposure, unique positions

---

## 7) Current Results Snapshot / 当前结果快照

As of latest baseline outputs and daily pipeline updates.

### 中文
基线汇总（baseline_summary）显示：
- Total return: 6.2780%
- Excess total return: 0.6608%
- Annualized return: 5.4335%
- Annualized volatility: 19.3747%
- Max drawdown: -22.3010%
- Information ratio: 0.0309

2026 YTD（2026-01-02 至 2026-03-23）：
- 模型累计收益：13.1881%
- 基准累计收益：-2.0694%
- 超额收益：15.2575%
- 交易日：55

### English
Baseline summary shows:
- Total return: 6.2780%
- Excess total return: 0.6608%
- Annualized return: 5.4335%
- Annualized volatility: 19.3747%
- Max drawdown: -22.3010%
- Information ratio: 0.0309

2026 YTD (2026-01-02 to 2026-03-23):
- Model cumulative return: 13.1881%
- Benchmark cumulative return: -2.0694%
- Excess return: 15.2575%
- Trading days: 55

---

## 8) Survivorship Bias Handling / 幸存者偏差处理

### 中文
已实现的控制：
- 使用动态 membership 区间过滤历史可交易池。
- 每日刷新 S&P 500 快照并重建 membership，使覆盖日期与市场日期同步。
- 质量日志记录 coverage 与 fallback 状态。

关键监控字段（data_quality_log）：
- latest_market_date
- membership_max_end_date
- membership_stale_days
- used_membership_fallback
- warning

当前状态（最新记录）：
- stale_days = 0
- fallback = 0
即：当前运行不存在“因成分过期导致的回退”问题。

### English
Implemented controls:
- Dynamic membership interval filtering for historical tradable universe.
- Daily S&P 500 snapshot refresh and membership rebuild to keep coverage current.
- Data-quality log to track coverage and fallback behavior.

Key fields in data_quality_log:
- latest_market_date
- membership_max_end_date
- membership_stale_days
- used_membership_fallback
- warning

Current status (latest log):
- stale_days = 0
- fallback = 0
Meaning no stale-membership fallback is active in current runs.

---

## 9) Daily & Weekly Operations / 日常与周度运营

### 中文
每日：
1) 自动任务触发 run_daily_simulation.py
2) 更新 membership 与价格数据
3) 更新持仓、交易动作、净值、质量日志
4) 输出 live 曲线与历史累积文件

每周（建议周五）：
1) 运行周度复盘
2) 对比周收益 vs 基准
3) 检查风险目标偏差与回撤
4) 评估是否需要参数微调

### English
Daily:
1) Scheduled run executes run_daily_simulation.py
2) Refresh membership and price data
3) Update positions, trades, NAV, and quality logs
4) Export live curve and cumulative history files

Weekly (recommended on Friday):
1) Run weekly review
2) Compare weekly return vs benchmark
3) Check risk-target gap and drawdown
4) Decide whether minor parameter adjustments are needed

---

## 10) Limitations & Risk Disclosure / 局限与风险披露

### 中文
- 回测与模拟不保证未来收益。
- 参数扫描存在过拟合风险，需坚持滚动验证。
- 数据源可能存在延迟、修订、停牌/退市处理差异。
- 当前策略为 long-only（短端能力未启用），在某些市场环境下可能相对劣势。

### English
- Backtests/simulations do not guarantee future performance.
- Parameter sweeps may overfit; rolling validation is required.
- Data sources can have delays, revisions, and treatment differences for delistings/suspensions.
- Current production setup is long-only; lack of active short sleeve may underperform in some regimes.

---

## 11) How to Explain to Professor / 面向教授的解释框架

### 中文（3分钟版）
1) 我们做的是短周期 EWMA 横截面动量，周频调仓，风险目标化控制。
2) 我们把策略做成了可审计流水线：每日数据更新、每日日志、交易历史、持仓历史、质量日志。
3) 我们显式控制了幸存者偏差：动态成分 + 覆盖监控 + 严格模式。
4) 结果上，模型在 2026 YTD 取得了显著正收益和正超额；同时我们保留完整风险披露与局限说明。

### English (3-minute pitch)
1) We implement a short-horizon EWMA cross-sectional momentum strategy with weekly rebalancing and volatility-targeted risk control.
2) The system is fully auditable: daily data refresh, daily logs, trade history, position history, and quality diagnostics.
3) Survivorship bias is explicitly controlled via dynamic membership, coverage monitoring, and strict mode.
4) Performance is positive with strong YTD excess return, while limitations and risk disclosures are transparently documented.

---

## 12) Key File Map / 关键文件索引

- src/config.py
- src/signals.py
- src/portfolio.py
- src/backtest.py
- src/metrics.py
- src/universe.py
- src/prepare_universe_membership.py
- run_baseline.py
- run_daily_simulation.py
- outputs/baseline_summary.csv
- outputs/baseline_daily_results.csv
- outputs/simulation/daily_log.csv
- outputs/simulation/trades_history.csv
- outputs/simulation/positions_history.csv
- outputs/simulation/data_quality_log.csv

---

Prepared for course reporting and weekly strategy review.
