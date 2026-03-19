from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src import config
from src.backtest import run_backtest
from src.data_loader import filter_date_range, load_prices
from src.download_data import download_prices, get_tickers, save_prices
from src.metrics import compute_summary
from src.prepare_universe_membership import refresh_membership_files
from src.plotting import plot_live_portfolio_value, plot_portfolio_value
from src.signals import add_momentum_signal
from src.universe import load_universe_membership


SIM_DIR = config.OUTPUT_DIR / "simulation"
WEEKLY_DIR = SIM_DIR / "weekly_reports"
DAILY_LOG_FILE = SIM_DIR / "daily_log.csv"
POSITIONS_FILE = SIM_DIR / "latest_positions.csv"
LATEST_TRADES_FILE = SIM_DIR / "latest_trades.csv"
TRADES_HISTORY_FILE = SIM_DIR / "trades_history.csv"
POSITIONS_HISTORY_FILE = SIM_DIR / "positions_history.csv"
LIVE_PLOT_FILE = SIM_DIR / "portfolio_value_live.png"
DATA_QUALITY_FILE = SIM_DIR / "data_quality_log.csv"


def _ensure_dirs() -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    SIM_DIR.mkdir(exist_ok=True)
    WEEKLY_DIR.mkdir(exist_ok=True)


def _market_end_date_str() -> str:
    # yfinance end date is exclusive, so request through tomorrow to include today's bar.
    return (pd.Timestamp.today().normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _refresh_membership_snapshot(enabled: bool = True) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if not enabled:
        return None, None

    previous_max = None
    if config.UNIVERSE_FILE.exists():
        previous = pd.read_csv(config.UNIVERSE_FILE)
        if not previous.empty and "end_date" in previous.columns:
            previous_max = pd.Timestamp(pd.to_datetime(previous["end_date"]).max())

    _, membership = refresh_membership_files(update_live_snapshot=True)
    new_max = pd.Timestamp(pd.to_datetime(membership["end_date"]).max()) if not membership.empty else None
    return previous_max, new_max


def _refresh_prices_incremental(ticker_source: str = "sp500") -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    existing = None
    old_max_date = None

    if config.PRICE_FILE.exists():
        existing = load_prices(price_file=config.PRICE_FILE)
        if not existing.empty:
            old_max_date = pd.Timestamp(existing[config.DATE_COL].max())

    if old_max_date is None:
        start_date = config.START_DATE
    else:
        # Re-download a short overlap window to heal revised bars/splits from Yahoo.
        start_date = (old_max_date - pd.Timedelta(days=10)).strftime("%Y-%m-%d")

    end_date = _market_end_date_str()
    tickers = get_tickers(source=ticker_source)
    fresh = download_prices(tickers=tickers, start=start_date, end=end_date)

    if existing is None or existing.empty:
        merged = fresh
    else:
        merged = pd.concat([existing, fresh], ignore_index=True)
        merged = (
            merged.sort_values([config.TICKER_COL, config.DATE_COL])
            .drop_duplicates(subset=[config.TICKER_COL, config.DATE_COL], keep="last")
            .reset_index(drop=True)
        )

    save_prices(merged, output_file=config.PRICE_FILE)
    new_max_date = pd.Timestamp(merged[config.DATE_COL].max()) if not merged.empty else None
    return old_max_date, new_max_date


def _resolve_membership_for_live(membership: pd.DataFrame | None, latest_price_date: pd.Timestamp) -> pd.DataFrame | None:
    if membership is None or membership.empty:
        return None

    max_membership_date = pd.Timestamp(membership["end_date"].max())
    if latest_price_date > max_membership_date:
        # Membership history may lag; fall back to all downloaded tickers for current live dates.
        return None
    return membership


def _get_membership_coverage_status(
    membership: pd.DataFrame | None, latest_price_date: pd.Timestamp
) -> dict[str, object]:
    if membership is None or membership.empty:
        return {
            "membership_available": False,
            "membership_max_end_date": pd.NaT,
            "membership_stale_days": pd.NA,
            "used_fallback": True,
            "warning": "membership_missing",
        }

    max_end_date = pd.Timestamp(membership["end_date"].max())
    stale_days = max(0, int((latest_price_date.normalize() - max_end_date.normalize()).days))
    used_fallback = latest_price_date > max_end_date

    warning = ""
    if used_fallback:
        warning = "membership_stale"

    return {
        "membership_available": True,
        "membership_max_end_date": max_end_date,
        "membership_stale_days": stale_days,
        "used_fallback": used_fallback,
        "warning": warning,
    }


def _run_pipeline(strict_membership: bool = False) -> tuple[pd.DataFrame, pd.Series, pd.Timestamp, dict[str, object]]:
    prices = load_prices()
    raw_latest_date = pd.Timestamp(prices[config.DATE_COL].max())
    rolling_start_date = max(pd.Timestamp(config.START_DATE), raw_latest_date - pd.Timedelta(days=420))
    prices = filter_date_range(
        prices,
        start_date=rolling_start_date.strftime("%Y-%m-%d"),
        end_date=_market_end_date_str(),
    )
    prices = add_momentum_signal(prices)
    membership = load_universe_membership()
    latest_price_date = pd.Timestamp(prices[config.DATE_COL].max())
    coverage_status = _get_membership_coverage_status(membership, latest_price_date)

    if strict_membership and bool(coverage_status["used_fallback"]):
        max_end = coverage_status["membership_max_end_date"]
        if pd.isna(max_end):
            raise ValueError(
                "Strict membership mode enabled but universe membership file is missing/empty. "
                "Update data/universe_membership.csv or run without --strict-membership."
            )
        raise ValueError(
            "Strict membership mode enabled but membership coverage is stale: "
            f"latest market date={latest_price_date.date()}, membership max end date={pd.Timestamp(max_end).date()}. "
            "Update data/universe_membership.csv or run without --strict-membership."
        )

    membership = _resolve_membership_for_live(membership, latest_price_date)

    results = run_backtest(prices, membership=membership)
    summary = compute_summary(results)

    results.to_csv(config.OUTPUT_DIR / "baseline_daily_results.csv", index=False)
    summary.to_frame(name="value").to_csv(config.OUTPUT_DIR / "baseline_summary.csv")
    plot_portfolio_value(results)

    return results, summary, latest_price_date, coverage_status


def _build_live_log_row(results: pd.DataFrame) -> pd.DataFrame:
    latest = results.iloc[[-1]].copy()
    latest["run_timestamp"] = pd.Timestamp.now().isoformat()
    latest_date = pd.Timestamp(latest.iloc[0]["date"]).normalize()

    latest_return = float(latest.iloc[0]["portfolio_return"])
    # Guardrail against data spikes from bad bars/symbol anomalies.
    if abs(latest_return) > 0.30:
        latest.loc[:, "portfolio_return"] = 0.0
        latest.loc[:, "gross_return"] = 0.0
        latest.loc[:, "benchmark_return"] = 0.0
        latest.loc[:, "excess_return"] = 0.0

    cols = [
        "date",
        "run_timestamp",
        "portfolio_value",
        "portfolio_nav",
        "portfolio_return",
        "benchmark_return",
        "excess_return",
        "gross_return",
        "turnover",
        "trading_cost",
        "short_borrow_cost",
        "gross_exposure",
        "net_exposure",
        "long_count",
        "short_count",
        "unique_positions",
        "is_rebalance_day",
        "signal_date",
        "long_tickers",
        "short_tickers",
        "weights_json",
    ]
    latest = latest[cols]

    prior_value = config.INITIAL_CAPITAL
    if DAILY_LOG_FILE.exists():
        existing = pd.read_csv(DAILY_LOG_FILE, parse_dates=["date"], keep_default_na=False)
        if not existing.empty:
            existing_dates = pd.to_datetime(existing["date"]).dt.normalize()
            same_day = existing.loc[existing_dates == latest_date]
            if not same_day.empty:
                prev_same_value = float(same_day.iloc[-1]["portfolio_value"])
                prev_same_return = float(same_day.iloc[-1]["portfolio_return"])
                denom = 1.0 + prev_same_return
                prior_value = prev_same_value / denom if denom > 0 else config.INITIAL_CAPITAL
            else:
                prior_value = float(existing.iloc[-1]["portfolio_value"])

    if prior_value <= 0 or prior_value > config.INITIAL_CAPITAL * 100:
        prior_value = config.INITIAL_CAPITAL

    updated_value = prior_value * (1.0 + float(latest.iloc[0]["portfolio_return"]))
    latest.loc[:, "portfolio_value"] = updated_value
    latest.loc[:, "portfolio_nav"] = updated_value / config.INITIAL_CAPITAL
    return latest


def _update_daily_log(results: pd.DataFrame) -> pd.DataFrame:
    latest = _build_live_log_row(results)

    if DAILY_LOG_FILE.exists():
        existing = pd.read_csv(DAILY_LOG_FILE, parse_dates=["date"], keep_default_na=False)
        combined = pd.concat([existing, latest], ignore_index=True)
        combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    else:
        combined = latest

    combined.to_csv(DAILY_LOG_FILE, index=False)
    return combined


def _update_positions_file(results: pd.DataFrame) -> None:
    latest = results.iloc[-1]
    weights = json.loads(latest.get("weights_json", "{}"))

    rows = []
    for ticker, weight in weights.items():
        side = "long" if weight > 0 else "short" if weight < 0 else "flat"
        rows.append({"ticker": ticker, "weight": float(weight), "side": side})

    positions = pd.DataFrame(rows).sort_values(["side", "weight"], ascending=[True, False])
    positions.to_csv(POSITIONS_FILE, index=False)


def _parse_weights_json(weights_json: str) -> dict[str, float]:
    if not isinstance(weights_json, str) or not weights_json.strip():
        return {}
    try:
        parsed = json.loads(weights_json)
    except json.JSONDecodeError:
        return {}
    return {str(k): float(v) for k, v in parsed.items()}


def _update_latest_trades_file(daily_log: pd.DataFrame) -> pd.DataFrame:
    latest = daily_log.iloc[-1]
    latest_date = pd.Timestamp(latest["date"]).date()
    curr_weights = _parse_weights_json(latest.get("weights_json", "{}"))

    prev_weights = {}
    if len(daily_log) > 1:
        prev = daily_log.iloc[-2]
        prev_weights = _parse_weights_json(prev.get("weights_json", "{}"))

    tickers = sorted(set(prev_weights) | set(curr_weights))
    rows = []
    for ticker in tickers:
        from_w = float(prev_weights.get(ticker, 0.0))
        to_w = float(curr_weights.get(ticker, 0.0))
        delta = to_w - from_w
        if abs(delta) < 1e-12:
            continue
        if from_w == 0.0 and to_w > 0.0:
            action = "BUY"
        elif from_w > 0.0 and to_w == 0.0:
            action = "SELL"
        elif delta > 0:
            action = "INCREASE"
        else:
            action = "DECREASE"

        rows.append(
            {
                "date": latest_date.isoformat(),
                "ticker": ticker,
                "action": action,
                "from_weight": from_w,
                "to_weight": to_w,
                "delta_weight": delta,
            }
        )

    trades = pd.DataFrame(rows)
    if trades.empty:
        trades = pd.DataFrame(
            [
                {
                    "date": latest_date.isoformat(),
                    "ticker": "(none)",
                    "action": "NO_CHANGE",
                    "from_weight": 0.0,
                    "to_weight": 0.0,
                    "delta_weight": 0.0,
                }
            ]
        )

    trades.to_csv(LATEST_TRADES_FILE, index=False)
    return trades


def _append_trades_history(trades: pd.DataFrame, daily_log: pd.DataFrame) -> pd.DataFrame:
    current = trades.copy()
    current["run_timestamp"] = str(daily_log.iloc[-1]["run_timestamp"])

    if TRADES_HISTORY_FILE.exists():
        history = pd.read_csv(TRADES_HISTORY_FILE, keep_default_na=False)
        combined = pd.concat([history, current], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last")
    else:
        combined = current

    combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)
    combined.to_csv(TRADES_HISTORY_FILE, index=False)
    return combined


def _append_positions_history(daily_log: pd.DataFrame) -> pd.DataFrame:
    latest = daily_log.iloc[-1]
    run_timestamp = str(latest["run_timestamp"])
    date_str = pd.Timestamp(latest["date"]).date().isoformat()
    weights = _parse_weights_json(latest.get("weights_json", "{}"))

    rows = []
    for ticker, weight in sorted(weights.items()):
        side = "long" if weight > 0 else "short" if weight < 0 else "flat"
        rows.append(
            {
                "date": date_str,
                "run_timestamp": run_timestamp,
                "ticker": ticker,
                "weight": float(weight),
                "side": side,
            }
        )

    if not rows:
        rows.append(
            {
                "date": date_str,
                "run_timestamp": run_timestamp,
                "ticker": "(none)",
                "weight": 0.0,
                "side": "flat",
            }
        )

    current = pd.DataFrame(rows)

    if POSITIONS_HISTORY_FILE.exists():
        history = pd.read_csv(POSITIONS_HISTORY_FILE, keep_default_na=False)
        combined = pd.concat([history, current], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last")
    else:
        combined = current

    combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)
    combined.to_csv(POSITIONS_HISTORY_FILE, index=False)
    return combined


def _update_data_quality_log(
    daily_log: pd.DataFrame,
    latest_price_date: pd.Timestamp,
    ticker_source: str,
    strict_membership: bool,
    coverage_status: dict[str, object],
) -> pd.DataFrame:
    latest = daily_log.iloc[-1]
    max_end = coverage_status.get("membership_max_end_date", pd.NaT)
    if pd.isna(max_end):
        max_end_text = ""
    else:
        max_end_text = pd.Timestamp(max_end).date().isoformat()

    row = pd.DataFrame(
        [
            {
                "date": pd.Timestamp(latest["date"]).date().isoformat(),
                "run_timestamp": str(latest["run_timestamp"]),
                "latest_market_date": latest_price_date.date().isoformat(),
                "ticker_source": ticker_source,
                "strict_membership": int(strict_membership),
                "membership_available": int(bool(coverage_status.get("membership_available", False))),
                "membership_max_end_date": max_end_text,
                "membership_stale_days": coverage_status.get("membership_stale_days", pd.NA),
                "used_membership_fallback": int(bool(coverage_status.get("used_fallback", False))),
                "warning": str(coverage_status.get("warning", "")),
            }
        ]
    )

    if DATA_QUALITY_FILE.exists():
        existing = pd.read_csv(DATA_QUALITY_FILE, keep_default_na=False)
        combined = pd.concat([existing, row], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date"], keep="last")
    else:
        combined = row

    combined = combined.sort_values("date").reset_index(drop=True)
    combined.to_csv(DATA_QUALITY_FILE, index=False)
    return combined


def _weekly_slice(results: pd.DataFrame) -> pd.DataFrame:
    latest_date = pd.Timestamp(results["date"].iloc[-1])
    week_start = latest_date - pd.Timedelta(days=6)
    return results.loc[results["date"] >= week_start].copy()


def _render_weekly_report(results: pd.DataFrame, summary: pd.Series) -> str:
    week = _weekly_slice(results)
    latest = week.iloc[-1]

    week_return = (1.0 + week["portfolio_return"].fillna(0.0)).prod() - 1.0
    week_benchmark = (1.0 + week["benchmark_return"].fillna(0.0)).prod() - 1.0
    week_excess = week_return - week_benchmark

    avg_turnover = float(week["turnover"].fillna(0.0).mean())
    avg_gross_exposure = float(week["gross_exposure"].fillna(0.0).mean())
    total_borrow_cost = float(week["short_borrow_cost"].fillna(0.0).sum())

    lines = [
        "# Weekly Simulation Report",
        "",
        f"Date: {pd.Timestamp(latest['date']).date()}",
        "",
        "## Weekly Summary",
        f"- Weekly portfolio return: {week_return:.4%}",
        f"- Weekly benchmark return: {week_benchmark:.4%}",
        f"- Weekly excess return: {week_excess:.4%}",
        f"- Ending portfolio value: ${float(latest['portfolio_value']):,.2f}",
        "",
        "## Risk and Trading",
        f"- Average turnover: {avg_turnover:.4f}",
        f"- Average gross exposure: {avg_gross_exposure:.4f}",
        f"- Total short borrow cost (week): {total_borrow_cost:.6f}",
        f"- Max drawdown (full sample): {float(summary['max_drawdown']):.4%}",
        "",
        "## Current Holdings",
        f"- Long count: {int(latest['long_count'])}",
        f"- Short count: {int(latest['short_count'])}",
        f"- Long tickers: {latest['long_tickers']}",
        f"- Short tickers: {latest['short_tickers']}",
        "",
        "## Next Week Plan",
        "- Re-run daily simulation after market close.",
        "- Validate data completeness and review exposure drift.",
        "- Keep weekly comparison versus benchmark and target risk.",
        "",
    ]
    return "\n".join(lines)


def _write_weekly_report(results: pd.DataFrame, summary: pd.Series) -> Path:
    latest_date = pd.Timestamp(results["date"].iloc[-1]).date()
    report_path = WEEKLY_DIR / f"weekly_report_{latest_date.isoformat()}.md"
    report_path.write_text(_render_weekly_report(results, summary), encoding="utf-8")
    return report_path


def main(
    force_weekly_report: bool = False,
    refresh_data: bool = True,
    ticker_source: str = "sp500",
    strict_membership: bool = False,
    refresh_membership: bool = True,
) -> None:
    _ensure_dirs()

    old_membership_max = None
    new_membership_max = None
    old_membership_max, new_membership_max = _refresh_membership_snapshot(enabled=refresh_membership)

    old_max_date = None
    new_max_date = None
    if refresh_data:
        old_max_date, new_max_date = _refresh_prices_incremental(ticker_source=ticker_source)

    results, summary, latest_price_date, coverage_status = _run_pipeline(
        strict_membership=strict_membership
    )

    daily_log = _update_daily_log(results)
    _update_positions_file(results)
    trades = _update_latest_trades_file(daily_log)
    trades_history = _append_trades_history(trades, daily_log)
    positions_history = _append_positions_history(daily_log)
    live_plot_path = plot_live_portfolio_value(daily_log, output_file=LIVE_PLOT_FILE)
    quality_log = _update_data_quality_log(
        daily_log=daily_log,
        latest_price_date=latest_price_date,
        ticker_source=ticker_source,
        strict_membership=strict_membership,
        coverage_status=coverage_status,
    )

    latest_date = pd.Timestamp(results["date"].iloc[-1])
    should_write_weekly = force_weekly_report or (latest_date.weekday() == 4)

    print("Daily simulation updated")
    if refresh_membership:
        print(
            "Membership refreshed: "
            f"old max={old_membership_max.date() if old_membership_max is not None else 'N/A'} | "
            f"new max={new_membership_max.date() if new_membership_max is not None else 'N/A'}"
        )
    if refresh_data:
        print(f"Price data refreshed: old max={old_max_date.date() if old_max_date is not None else 'N/A'} | new max={new_max_date.date() if new_max_date is not None else 'N/A'}")
    print(f"Latest market data date: {latest_price_date.date()}")
    print(f"Latest date: {latest_date.date()}")
    print(f"Portfolio value: ${float(daily_log.iloc[-1]['portfolio_value']):,.2f}")
    print(f"Daily return: {float(daily_log.iloc[-1]['portfolio_return']):.4%}")
    print(f"Model total return (rolling window): {float(summary['total_return']):.4%}")
    print(f"Daily log rows: {len(daily_log)}")
    print(f"Daily log file: {DAILY_LOG_FILE}")
    print(f"Positions file: {POSITIONS_FILE}")
    print(f"Latest trades file: {LATEST_TRADES_FILE}")
    print(f"Latest trade actions: {len(trades)}")
    print(f"Trades history rows: {len(trades_history)} | file: {TRADES_HISTORY_FILE}")
    print(f"Positions history rows: {len(positions_history)} | file: {POSITIONS_HISTORY_FILE}")
    print(f"Live portfolio chart: {live_plot_path}")
    print(f"Data quality log rows: {len(quality_log)} | file: {DATA_QUALITY_FILE}")

    if bool(coverage_status.get("used_fallback", False)):
        max_end = coverage_status.get("membership_max_end_date", pd.NaT)
        max_end_text = "N/A" if pd.isna(max_end) else pd.Timestamp(max_end).date().isoformat()
        stale_days = coverage_status.get("membership_stale_days", "N/A")
        print(
            "WARNING: Universe membership coverage does not reach latest market date. "
            f"membership_max_end_date={max_end_text}, stale_days={stale_days}. "
            "This can introduce survivorship bias. "
            "Use --strict-membership to fail-fast until membership data is updated."
        )

    if should_write_weekly:
        report_path = _write_weekly_report(results, summary)
        print(f"Weekly report generated: {report_path}")
    else:
        print("Weekly report not generated today (use --force-weekly-report to generate).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run daily live-like simulation update with latest Yahoo data and optional weekly report."
    )
    parser.add_argument(
        "--force-weekly-report",
        action="store_true",
        help="Generate weekly report regardless of weekday.",
    )
    parser.add_argument(
        "--no-refresh-data",
        action="store_true",
        help="Skip Yahoo data refresh and reuse existing data/prices.csv.",
    )
    parser.add_argument(
        "--no-refresh-membership",
        action="store_true",
        help="Skip live membership snapshot refresh and reuse existing universe_membership.csv.",
    )
    parser.add_argument(
        "--ticker-source",
        choices=["membership", "sp500", "file"],
        default="sp500",
        help="Ticker source for data refresh.",
    )
    parser.add_argument(
        "--strict-membership",
        action="store_true",
        help="Fail if membership file is missing/stale relative to latest market date.",
    )
    args = parser.parse_args()
    main(
        force_weekly_report=args.force_weekly_report,
        refresh_data=not args.no_refresh_data,
        ticker_source=args.ticker_source,
        strict_membership=args.strict_membership,
        refresh_membership=not args.no_refresh_membership,
    )
