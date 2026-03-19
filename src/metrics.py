import numpy as np
import pandas as pd

from . import config


TRADING_DAYS = 252


def compute_summary(results):
    returns = results["portfolio_return"].fillna(0.0)
    benchmark_returns = results.get("benchmark_return", pd.Series(0.0, index=results.index)).fillna(0.0)
    excess_returns = results.get("excess_return", returns - benchmark_returns).fillna(0.0)

    portfolio_value = results["portfolio_value"]
    normalized_nav = portfolio_value / config.INITIAL_CAPITAL
    benchmark_nav = (1.0 + benchmark_returns).cumprod()

    total_return = normalized_nav.iloc[-1] - 1.0
    total_pnl = portfolio_value.iloc[-1] - config.INITIAL_CAPITAL
    annualized_return = (normalized_nav.iloc[-1] ** (TRADING_DAYS / max(len(normalized_nav), 1))) - 1.0
    annualized_vol = returns.std(ddof=0) * np.sqrt(TRADING_DAYS)
    sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0.0

    benchmark_total_return = benchmark_nav.iloc[-1] - 1.0
    benchmark_annualized_return = (benchmark_nav.iloc[-1] ** (TRADING_DAYS / max(len(benchmark_nav), 1))) - 1.0
    tracking_error = excess_returns.std(ddof=0) * np.sqrt(TRADING_DAYS)
    information_ratio = (
        (annualized_return - benchmark_annualized_return) / tracking_error if tracking_error > 0 else 0.0
    )

    running_max = normalized_nav.cummax()
    drawdown = normalized_nav / running_max - 1.0
    max_drawdown = drawdown.min()

    avg_turnover = results["turnover"].fillna(0.0).mean()
    avg_short_exposure = results.get("short_exposure", pd.Series(0.0, index=results.index)).fillna(0.0).mean()
    avg_gross_exposure = results.get("gross_exposure", pd.Series(0.0, index=results.index)).fillna(0.0).mean()
    avg_short_borrow_cost = (
        results.get("short_borrow_cost", pd.Series(0.0, index=results.index)).fillna(0.0).mean()
    )
    avg_unique_positions = (
        results.get("unique_positions", pd.Series(0, index=results.index)).fillna(0.0).mean()
    )

    achieved_risk_gap = annualized_vol - config.TARGET_ANNUAL_VOLATILITY
    meets_min_positions = avg_unique_positions >= config.MIN_UNIQUE_SECURITIES

    return pd.Series(
        {
            "total_return": total_return,
            "benchmark_total_return": benchmark_total_return,
            "excess_total_return": total_return - benchmark_total_return,
            "total_pnl_usd": total_pnl,
            "ending_portfolio_value_usd": portfolio_value.iloc[-1],
            "annualized_return": annualized_return,
            "benchmark_annualized_return": benchmark_annualized_return,
            "annualized_volatility": annualized_vol,
            "target_annualized_volatility": config.TARGET_ANNUAL_VOLATILITY,
            "risk_target_gap": achieved_risk_gap,
            "sharpe_ratio": sharpe,
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
            "max_drawdown": max_drawdown,
            "average_turnover": avg_turnover,
            "average_short_exposure": avg_short_exposure,
            "average_gross_exposure": avg_gross_exposure,
            "average_short_borrow_cost": avg_short_borrow_cost,
            "average_unique_positions": avg_unique_positions,
            "meets_min_unique_positions": float(meets_min_positions),
        }
    )
