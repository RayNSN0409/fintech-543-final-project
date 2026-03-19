from pathlib import Path

import pandas as pd

from src import config
from src.backtest import run_backtest
from src.data_loader import filter_date_range, load_prices
from src.metrics import compute_summary
from src.plotting import plot_portfolio_value
from src.signals import add_momentum_signal
from src.universe import load_universe_membership


def format_summary(summary):
    formatted = {}
    for key, value in summary.items():
        if key.endswith("_usd"):
            formatted[key] = f"{float(value):,.2f}"
        else:
            formatted[key] = f"{float(value):.4f}"
    return formatted


def main():
    prices = load_prices()
    prices = filter_date_range(prices)
    prices = add_momentum_signal(prices)
    membership = load_universe_membership()

    results = run_backtest(prices, membership=membership)
    summary = compute_summary(results)

    config.OUTPUT_DIR.mkdir(exist_ok=True)
    results.to_csv(config.OUTPUT_DIR / "baseline_daily_results.csv", index=False)
    summary.to_frame(name="value").to_csv(config.OUTPUT_DIR / "baseline_summary.csv")
    chart_path = plot_portfolio_value(results)

    print("Baseline backtest summary")
    print(
        f"Momentum method: {config.MOMENTUM_METHOD} | "
        f"Score mode: {config.MOMENTUM_SCORE_MODE} | "
        f"Lookback: {config.LOOKBACK_DAYS} | "
        f"EWMA halflife: {config.EWMA_HALFLIFE_DAYS}"
    )
    print(f"Rebalance weekday (0=Mon,...,4=Fri): {config.REBALANCE_WEEKDAY}")
    print(
        f"Target vol: {config.TARGET_ANNUAL_VOLATILITY:.2%} | "
        f"Max gross leverage: {config.MAX_GROSS_LEVERAGE:.2f} | "
        f"Min signal price: {config.MIN_SIGNAL_PRICE:.2f}"
    )
    print(
        f"Base long/short: {config.LONG_BOOK_WEIGHT:.2f}/{config.SHORT_BOOK_WEIGHT:.2f} | "
        f"Trend switch: {config.USE_BENCHMARK_TREND_SWITCH}"
    )
    if membership is not None:
        print("Using dynamic universe membership from data/universe_membership.csv")
    else:
        print("No dynamic universe file found; using all tickers present in prices.csv")

    if len(results) < config.MIN_BACKTEST_TRADING_DAYS:
        print(
            "WARNING: Backtest window is shorter than 4 weeks of trading days "
            f"({len(results)} < {config.MIN_BACKTEST_TRADING_DAYS})."
        )

    for key, value in format_summary(summary).items():
        print(f"{key:<28} {value}")
    print(f"\nDaily results saved to: {config.OUTPUT_DIR / 'baseline_daily_results.csv'}")
    print(f"Summary saved to: {config.OUTPUT_DIR / 'baseline_summary.csv'}")
    print(f"Chart saved to: {chart_path}")


if __name__ == "__main__":
    main()
