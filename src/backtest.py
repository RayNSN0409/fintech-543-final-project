import pandas as pd

from . import config
from .portfolio import select_top_n, target_weights
from .signals import get_rebalance_dates, get_signal_frame
from .universe import get_eligible_tickers


def _build_price_frames(prices):
    close_wide = prices.pivot(index=config.DATE_COL, columns=config.TICKER_COL, values=config.CLOSE_COL).sort_index()
    open_wide = prices.pivot(index=config.DATE_COL, columns=config.TICKER_COL, values=config.OPEN_COL).sort_index()
    return close_wide, open_wide


def _next_trading_date(trading_dates, signal_date):
    later_dates = trading_dates[trading_dates > signal_date]
    return later_dates.min() if len(later_dates) else None


def run_backtest(prices, membership=None):
    prices = prices.copy()
    close_wide, open_wide = _build_price_frames(prices)
    trading_dates = close_wide.index
    rebalance_dates = get_rebalance_dates(prices)

    signal_to_trade_date = {}
    for signal_date in rebalance_dates:
        trade_date = _next_trading_date(trading_dates, signal_date)
        if trade_date is not None:
            signal_to_trade_date[pd.Timestamp(signal_date)] = pd.Timestamp(trade_date)

    target_weights_by_trade_date = {}
    for signal_date, trade_date in signal_to_trade_date.items():
        eligible_tickers = get_eligible_tickers(membership, signal_date)
        signal_frame = get_signal_frame(prices, signal_date, eligible_tickers=eligible_tickers)
        selected = select_top_n(signal_frame)
        target_weights_by_trade_date[trade_date] = target_weights(selected)

    current_weights = {}
    portfolio_value = config.INITIAL_CAPITAL
    records = []

    for idx, date in enumerate(trading_dates):
        date = pd.Timestamp(date)
        turnover = 0.0
        trading_cost = 0.0

        if date in target_weights_by_trade_date:
            new_weights = target_weights_by_trade_date[date]
            all_tickers = sorted(set(current_weights) | set(new_weights))
            turnover = sum(abs(new_weights.get(t, 0.0) - current_weights.get(t, 0.0)) for t in all_tickers)
            trading_cost = turnover * (config.TRANSACTION_COST_BPS / 10000.0)
            current_weights = new_weights

        if idx == 0:
            daily_return = 0.0
        elif date in target_weights_by_trade_date:
            intraday_returns = close_wide.loc[date] / open_wide.loc[date] - 1.0
            daily_return = sum(
                weight * intraday_returns.get(ticker, 0.0) for ticker, weight in current_weights.items()
            )
        else:
            prev_date = trading_dates[idx - 1]
            day_returns = close_wide.loc[date] / close_wide.loc[prev_date] - 1.0
            daily_return = sum(weight * day_returns.get(ticker, 0.0) for ticker, weight in current_weights.items())

        net_return = daily_return - trading_cost
        portfolio_value *= 1.0 + net_return

        records.append(
            {
                "date": date,
                "portfolio_return": net_return,
                "gross_return": daily_return,
                "turnover": turnover,
                "trading_cost": trading_cost,
                "portfolio_value": portfolio_value,
                "portfolio_nav": portfolio_value / config.INITIAL_CAPITAL,
            }
        )

    return pd.DataFrame(records)
