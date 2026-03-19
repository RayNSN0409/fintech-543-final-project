import pandas as pd

from . import config


REQUIRED_COLUMNS = {
    config.DATE_COL,
    config.TICKER_COL,
    config.OPEN_COL,
    config.CLOSE_COL,
}


def load_prices(price_file=None):
    if price_file is None:
        price_file = config.PRICE_FILE

    prices = pd.read_csv(price_file)
    missing = REQUIRED_COLUMNS - set(prices.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    prices = prices.copy()
    prices[config.DATE_COL] = pd.to_datetime(prices[config.DATE_COL])
    prices = prices.sort_values([config.TICKER_COL, config.DATE_COL]).reset_index(drop=True)
    return prices


def filter_date_range(prices, start_date=None, end_date=None):
    if start_date is None:
        start_date = config.START_DATE
    if end_date is None:
        end_date = config.END_DATE

    mask = (prices[config.DATE_COL] >= pd.Timestamp(start_date)) & (
        prices[config.DATE_COL] <= pd.Timestamp(end_date)
    )
    return prices.loc[mask].copy()
