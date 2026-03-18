import numpy as np
import pandas as pd

from . import config


TRADING_DAYS = 252


def compute_summary(results):
    returns = results["portfolio_return"].fillna(0.0)
    portfolio_value = results["portfolio_value"]
    normalized_nav = portfolio_value / config.INITIAL_CAPITAL

    total_return = normalized_nav.iloc[-1] - 1.0
    total_pnl = portfolio_value.iloc[-1] - config.INITIAL_CAPITAL
    annualized_return = (normalized_nav.iloc[-1] ** (TRADING_DAYS / max(len(normalized_nav), 1))) - 1.0
    annualized_vol = returns.std(ddof=0) * np.sqrt(TRADING_DAYS)
    sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0.0

    running_max = normalized_nav.cummax()
    drawdown = normalized_nav / running_max - 1.0
    max_drawdown = drawdown.min()

    avg_turnover = results["turnover"].fillna(0.0).mean()

    return pd.Series(
        {
            "total_return": total_return,
            "total_pnl_usd": total_pnl,
            "ending_portfolio_value_usd": portfolio_value.iloc[-1],
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "average_turnover": avg_turnover,
        }
    )
