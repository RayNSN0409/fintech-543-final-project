import matplotlib.pyplot as plt
import pandas as pd

from . import config


def plot_portfolio_value(results, output_file=None):
    if output_file is None:
        output_file = config.OUTPUT_DIR / "baseline_portfolio_value.png"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(results["date"], results["portfolio_value"], linewidth=2, label="Portfolio Value")
    ax.set_title("Cross-Sectional Momentum Portfolio Value")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value (USD)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return output_file


def plot_live_portfolio_value(daily_log, output_file=None):
    if output_file is None:
        output_file = config.OUTPUT_DIR / "simulation" / "portfolio_value_live.png"

    frame = daily_log.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(frame["date"], frame["portfolio_value"], linewidth=2, label="Live Portfolio Value")
    ax.set_title("Live Simulation Portfolio Value")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value (USD)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return output_file
