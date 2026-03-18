import pandas as pd

from . import config


def add_momentum_signal(prices, lookback_days=config.LOOKBACK_DAYS):
    prices = prices.copy()
    prices["momentum"] = prices.groupby(config.TICKER_COL)[config.CLOSE_COL].pct_change(lookback_days)
    return prices


def get_rebalance_dates(prices, weekday=config.REBALANCE_WEEKDAY):
    unique_dates = pd.Series(sorted(prices[config.DATE_COL].dropna().unique()))
    return [date for date in unique_dates if pd.Timestamp(date).weekday() == weekday]


def get_signal_frame(prices, signal_date, eligible_tickers=None):
    frame = prices.loc[prices[config.DATE_COL] == signal_date, [config.TICKER_COL, "momentum"]].copy()
    if eligible_tickers is not None:
        frame = frame.loc[frame[config.TICKER_COL].isin(eligible_tickers)]
    frame = frame.dropna(subset=["momentum"])
    frame = frame.sort_values("momentum", ascending=False).reset_index(drop=True)
    return frame
