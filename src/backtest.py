import json

import pandas as pd

from . import config
from .portfolio import build_long_short_weights
from .signals import get_rebalance_dates, get_signal_frame
from .universe import get_eligible_tickers


def _build_price_frames(prices):
    close_wide = prices.pivot(index=config.DATE_COL, columns=config.TICKER_COL, values=config.CLOSE_COL).sort_index()
    open_wide = prices.pivot(index=config.DATE_COL, columns=config.TICKER_COL, values=config.OPEN_COL).sort_index()
    return close_wide, open_wide


def _next_trading_date(trading_dates, signal_date):
    later_dates = trading_dates[trading_dates > signal_date]
    return later_dates.min() if len(later_dates) else None


def _daily_target_volatility():
    return config.TARGET_ANNUAL_VOLATILITY / (config.TRADING_DAYS_PER_YEAR ** 0.5)


def _realized_daily_volatility(history_returns, lookback_days):
    if len(history_returns) < 2:
        return None

    window = pd.Series(history_returns[-lookback_days:])
    vol = float(window.std(ddof=0))
    return vol if vol > 0 else None


def _scale_weights_for_risk(raw_weights, history_returns):
    if not raw_weights:
        return {}, 0.0

    realized_daily_vol = _realized_daily_volatility(history_returns, config.VOL_LOOKBACK_DAYS)
    if realized_daily_vol is None:
        scale = 1.0
    else:
        scale = _daily_target_volatility() / realized_daily_vol

    gross_before_cap = sum(abs(weight) for weight in raw_weights.values())
    max_scale_for_gross = (
        config.MAX_GROSS_LEVERAGE / gross_before_cap if gross_before_cap > 0 else 0.0
    )
    scale = max(0.0, min(scale, max_scale_for_gross))

    scaled_weights = {ticker: weight * scale for ticker, weight in raw_weights.items()}
    return scaled_weights, scale


def _weighted_return(weights, returns_row):
    if not weights:
        return 0.0

    weight_series = pd.Series(weights)
    aligned_returns = returns_row.reindex(weight_series.index).fillna(0.0)
    return float((weight_series * aligned_returns).sum())


def _short_exposure(weights):
    return float(sum(-weight for weight in weights.values() if weight < 0.0))


def _serialize_weights(weights):
    if not weights:
        return "{}"
    serializable = {ticker: float(weight) for ticker, weight in sorted(weights.items())}
    return json.dumps(serializable, separators=(",", ":"))


def _book_weights_for_signal_date(benchmark_close, signal_date):
    if not config.USE_BENCHMARK_TREND_SWITCH:
        return config.LONG_BOOK_WEIGHT, config.SHORT_BOOK_WEIGHT

    history = benchmark_close.loc[benchmark_close.index <= signal_date].dropna()
    if len(history) < config.TREND_LOOKBACK_DAYS:
        return config.LONG_BOOK_WEIGHT, config.SHORT_BOOK_WEIGHT

    rolling_mean = history.tail(config.TREND_LOOKBACK_DAYS).mean()
    last_close = history.iloc[-1]

    if last_close >= rolling_mean:
        return config.BULL_LONG_BOOK_WEIGHT, config.BULL_SHORT_BOOK_WEIGHT
    return config.BEAR_LONG_BOOK_WEIGHT, config.BEAR_SHORT_BOOK_WEIGHT


def run_backtest(prices, membership=None):
    prices = prices.copy()
    close_wide, open_wide = _build_price_frames(prices)
    trading_dates = close_wide.index
    rebalance_dates = get_rebalance_dates(prices)
    benchmark = config.BENCHMARK_TICKER
    benchmark_close = close_wide.get(benchmark, pd.Series(dtype=float))

    signal_to_trade_date = {}
    for signal_date in rebalance_dates:
        trade_date = _next_trading_date(trading_dates, signal_date)
        if trade_date is not None:
            signal_to_trade_date[pd.Timestamp(signal_date)] = pd.Timestamp(trade_date)

    signal_frames_by_trade_date = {}

    for signal_date, trade_date in signal_to_trade_date.items():
        eligible_tickers = get_eligible_tickers(membership, signal_date)
        signal_frame = get_signal_frame(prices, signal_date, eligible_tickers=eligible_tickers)
        long_book_weight, short_book_weight = _book_weights_for_signal_date(benchmark_close, signal_date)
        signal_frames_by_trade_date[trade_date] = {
            "signal_frame": signal_frame,
            "signal_date": signal_date,
            "long_book_weight": long_book_weight,
            "short_book_weight": short_book_weight,
        }

    current_weights = {}
    portfolio_value = config.INITIAL_CAPITAL
    records = []
    historical_net_returns = []

    for idx, date in enumerate(trading_dates):
        date = pd.Timestamp(date)
        turnover = 0.0
        trading_cost = 0.0
        leverage_multiplier = 0.0
        signal_date = pd.NaT
        is_rebalance_day = False

        if date in signal_frames_by_trade_date:
            rebalance_payload = signal_frames_by_trade_date[date]
            signal_frame = rebalance_payload["signal_frame"]
            signal_date = rebalance_payload["signal_date"]
            is_rebalance_day = True
            raw_weights = build_long_short_weights(
                signal_frame,
                long_book_weight=rebalance_payload["long_book_weight"],
                short_book_weight=rebalance_payload["short_book_weight"],
                excluded_tickers={benchmark},
            )
            new_weights, leverage_multiplier = _scale_weights_for_risk(raw_weights, historical_net_returns)

            all_tickers = sorted(set(current_weights) | set(new_weights))
            turnover = sum(abs(new_weights.get(t, 0.0) - current_weights.get(t, 0.0)) for t in all_tickers)
            trading_cost = turnover * (config.TRANSACTION_COST_BPS / 10000.0)
            current_weights = new_weights
        else:
            leverage_multiplier = sum(abs(weight) for weight in current_weights.values())

        if idx == 0:
            daily_return = 0.0
            benchmark_return = 0.0
        elif date in signal_frames_by_trade_date:
            intraday_returns = close_wide.loc[date] / open_wide.loc[date] - 1.0
            daily_return = _weighted_return(current_weights, intraday_returns)
            benchmark_open = open_wide.loc[date].get(benchmark, pd.NA)
            benchmark_close = close_wide.loc[date].get(benchmark, pd.NA)
            if pd.isna(benchmark_open) or pd.isna(benchmark_close) or benchmark_open == 0:
                benchmark_return = 0.0
            else:
                benchmark_return = float(benchmark_close / benchmark_open - 1.0)
        else:
            prev_date = trading_dates[idx - 1]
            day_returns = close_wide.loc[date] / close_wide.loc[prev_date] - 1.0
            daily_return = _weighted_return(current_weights, day_returns)

            benchmark_prev = close_wide.loc[prev_date].get(benchmark, pd.NA)
            benchmark_close = close_wide.loc[date].get(benchmark, pd.NA)
            if pd.isna(benchmark_prev) or pd.isna(benchmark_close) or benchmark_prev == 0:
                benchmark_return = 0.0
            else:
                benchmark_return = float(benchmark_close / benchmark_prev - 1.0)

        short_borrow_cost = _short_exposure(current_weights) * (
            config.SHORT_BORROW_RATE_ANNUAL / config.TRADING_DAYS_PER_YEAR
        )

        long_tickers = sorted([ticker for ticker, weight in current_weights.items() if weight > 0.0])
        short_tickers = sorted([ticker for ticker, weight in current_weights.items() if weight < 0.0])

        net_return = daily_return - trading_cost - short_borrow_cost
        excess_return = net_return - benchmark_return
        portfolio_value *= 1.0 + net_return
        historical_net_returns.append(net_return)

        records.append(
            {
                "date": date,
                "portfolio_return": net_return,
                "gross_return": daily_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "turnover": turnover,
                "trading_cost": trading_cost,
                "short_borrow_cost": short_borrow_cost,
                "short_exposure": _short_exposure(current_weights),
                "gross_exposure": float(sum(abs(weight) for weight in current_weights.values())),
                "net_exposure": float(sum(current_weights.values())),
                "unique_positions": int(len(current_weights)),
                "long_count": int(len(long_tickers)),
                "short_count": int(len(short_tickers)),
                "long_tickers": ";".join(long_tickers),
                "short_tickers": ";".join(short_tickers),
                "weights_json": _serialize_weights(current_weights),
                "is_rebalance_day": int(is_rebalance_day),
                "signal_date": signal_date,
                "leverage_multiplier": leverage_multiplier,
                "portfolio_value": portfolio_value,
                "portfolio_nav": portfolio_value / config.INITIAL_CAPITAL,
            }
        )

    return pd.DataFrame(records)
