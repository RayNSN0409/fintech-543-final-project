from __future__ import annotations

import argparse
import json

import pandas as pd

from src import config
from src.backtest import run_backtest
from src.data_loader import filter_date_range, load_prices
from src.signals import add_momentum_signal
from src.universe import load_universe_membership


OUTPUT_FILE = config.OUTPUT_DIR / "simulation" / "improved_model_last2days.csv"


def _prepare_live_like_prices(window_days: int) -> pd.DataFrame:
    prices = load_prices()
    latest_date = pd.Timestamp(prices[config.DATE_COL].max())
    rolling_start_date = max(pd.Timestamp(config.START_DATE), latest_date - pd.Timedelta(days=window_days))
    prices = filter_date_range(
        prices,
        start_date=rolling_start_date.strftime("%Y-%m-%d"),
        end_date=(pd.Timestamp.today().normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
    )
    return add_momentum_signal(prices)


def _run_with_overrides(prices: pd.DataFrame, membership: pd.DataFrame | None, overrides: dict) -> pd.DataFrame:
    old_values = {name: getattr(config, name) for name in overrides}
    try:
        for name, value in overrides.items():
            setattr(config, name, value)

        stop_config = {
            "fixed_position_stop_pct": float(config.FIXED_POSITION_STOP_PCT) if config.ENABLE_FIXED_POSITION_STOP else 0.0,
            "effective_start_date": config.STOP_LIVE_EFFECTIVE_DATE,
        }
        return run_backtest(prices, membership=membership, stop_config=stop_config)
    finally:
        for name, value in old_values.items():
            setattr(config, name, value)


def _max_abs_weight(weights_json: str) -> float:
    if not isinstance(weights_json, str) or not weights_json:
        return 0.0
    try:
        weights = json.loads(weights_json)
    except json.JSONDecodeError:
        return 0.0
    if not weights:
        return 0.0
    return float(max(abs(float(weight)) for weight in weights.values()))


def _effective_positions(weights_json: str) -> float:
    if not isinstance(weights_json, str) or not weights_json:
        return 0.0
    try:
        weights = json.loads(weights_json)
    except json.JSONDecodeError:
        return 0.0
    abs_weights = [abs(float(weight)) for weight in weights.values()]
    denom = sum(weight * weight for weight in abs_weights)
    if denom <= 0:
        return 0.0
    return float(1.0 / denom)


def _build_last_n_day_report(baseline: pd.DataFrame, improved: pd.DataFrame, last_n_days: int) -> pd.DataFrame:
    baseline_view = baseline[["date", "portfolio_return", "benchmark_return", "excess_return"]].rename(
        columns={
            "portfolio_return": "baseline_return",
            "benchmark_return": "spy_return",
            "excess_return": "baseline_excess",
        }
    )

    improved_view = improved[
        ["date", "portfolio_return", "excess_return", "unique_positions", "weights_json"]
    ].rename(
        columns={
            "portfolio_return": "improved_return",
            "excess_return": "improved_excess",
            "unique_positions": "improved_unique_positions",
        }
    )

    merged = baseline_view.merge(improved_view, on="date", how="inner").sort_values("date")
    merged["improved_vs_baseline_excess_gap"] = merged["improved_excess"] - merged["baseline_excess"]
    merged["improved_max_abs_weight"] = merged["weights_json"].map(_max_abs_weight)
    merged["improved_effective_positions"] = merged["weights_json"].map(_effective_positions)
    merged = merged.drop(columns=["weights_json"])
    return merged.tail(last_n_days).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare baseline model and a more diversified model for the latest trading days."
    )
    parser.add_argument("--window-days", type=int, default=420, help="Rolling window length used in live-like simulation.")
    parser.add_argument("--last-n-days", type=int, default=2, help="How many recent trading days to report.")
    parser.add_argument("--diversified-n-long", type=int, default=30, help="Number of long names in diversified model.")
    parser.add_argument(
        "--diversified-min-unique",
        type=int,
        default=20,
        help="Minimum unique holdings required in diversified model.",
    )
    args = parser.parse_args()

    prices = _prepare_live_like_prices(window_days=args.window_days)
    membership = load_universe_membership()

    baseline_results = _run_with_overrides(prices, membership, overrides={})
    improved_results = _run_with_overrides(
        prices,
        membership,
        overrides={
            "N_LONG": int(args.diversified_n_long),
            "MIN_UNIQUE_SECURITIES": int(args.diversified_min_unique),
        },
    )

    report = _build_last_n_day_report(baseline_results, improved_results, last_n_days=args.last_n_days)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(OUTPUT_FILE, index=False)

    print("Diversified model comparison (latest days)")
    print(report.to_string(index=False))
    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
