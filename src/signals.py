import pandas as pd

from . import config


def add_momentum_signal(
    prices,
    lookback_days=None,
    method=None,
    score_mode=None,
    ewma_halflife_days=None,
    ewma_min_periods=None,
    ewma_vol_halflife_days=None,
    ewma_vol_min_periods=None,
):
    if lookback_days is None:
        lookback_days = config.LOOKBACK_DAYS
    if method is None:
        method = config.MOMENTUM_METHOD
    if score_mode is None:
        score_mode = config.MOMENTUM_SCORE_MODE
    if ewma_halflife_days is None:
        ewma_halflife_days = config.EWMA_HALFLIFE_DAYS
    if ewma_min_periods is None:
        ewma_min_periods = config.EWMA_MIN_PERIODS
    if ewma_vol_halflife_days is None:
        ewma_vol_halflife_days = config.EWMA_VOL_HALFLIFE_DAYS
    if ewma_vol_min_periods is None:
        ewma_vol_min_periods = config.EWMA_VOL_MIN_PERIODS

    prices = prices.copy()
    grouped_close = prices.groupby(config.TICKER_COL)[config.CLOSE_COL]

    if method == "ewma":
        daily_returns = grouped_close.pct_change(1)
        ewma_mean = (
            daily_returns.groupby(prices[config.TICKER_COL])
            .transform(
                lambda series: series.ewm(
                    halflife=ewma_halflife_days,
                    min_periods=ewma_min_periods,
                    adjust=False,
                ).mean()
            )
        )

        if score_mode == "raw":
            prices["momentum"] = ewma_mean
        elif score_mode == "risk_adjusted":
            ewma_vol = (
                daily_returns.groupby(prices[config.TICKER_COL])
                .transform(
                    lambda series: series.ewm(
                        halflife=ewma_vol_halflife_days,
                        min_periods=ewma_vol_min_periods,
                        adjust=False,
                    ).std(bias=False)
                )
            )
            prices["momentum"] = ewma_mean / ewma_vol.replace(0.0, pd.NA)
        else:
            raise ValueError(f"Unsupported momentum score mode: {score_mode}")
    elif method == "simple":
        prices["momentum"] = grouped_close.pct_change(lookback_days)
    else:
        raise ValueError(f"Unsupported momentum method: {method}")

    return prices


def get_rebalance_dates(prices, weekday=None):
    if weekday is None:
        weekday = config.REBALANCE_WEEKDAY

    unique_dates = pd.Series(sorted(prices[config.DATE_COL].dropna().unique()))
    return [date for date in unique_dates if pd.Timestamp(date).weekday() == weekday]


def get_signal_frame(prices, signal_date, eligible_tickers=None, min_signal_price=None):
    if min_signal_price is None:
        min_signal_price = config.MIN_SIGNAL_PRICE

    frame = prices.loc[
        prices[config.DATE_COL] == signal_date,
        [config.TICKER_COL, config.CLOSE_COL, "momentum"],
    ].copy()
    if eligible_tickers is not None:
        frame = frame.loc[frame[config.TICKER_COL].isin(eligible_tickers)]
    if min_signal_price is not None:
        frame = frame.loc[frame[config.CLOSE_COL] >= float(min_signal_price)]

    frame = frame.dropna(subset=["momentum"])
    frame = frame.sort_values("momentum", ascending=False).reset_index(drop=True)
    return frame[[config.TICKER_COL, "momentum"]]
