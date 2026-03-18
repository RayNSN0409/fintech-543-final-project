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
    if membership is not None:
        print("Using dynamic universe membership from data/universe_membership.csv")
    else:
        print("No dynamic universe file found; using all tickers present in prices.csv")
    for key, value in format_summary(summary).items():
        print(f"{key:<28} {value}")
    print(f"\nDaily results saved to: {config.OUTPUT_DIR / 'baseline_daily_results.csv'}")
    print(f"Summary saved to: {config.OUTPUT_DIR / 'baseline_summary.csv'}")
    print(f"Chart saved to: {chart_path}")


if __name__ == "__main__":
    main()
