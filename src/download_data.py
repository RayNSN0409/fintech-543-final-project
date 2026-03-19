from pathlib import Path
from io import StringIO
from urllib.request import Request, urlopen
import re

import pandas as pd
import yfinance as yf

from . import config


DEFAULT_START_DATE = config.START_DATE
DEFAULT_END_DATE = config.END_DATE
DEFAULT_TICKER_SOURCE = "sp500"


TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")


def _sanitize_tickers(raw_tickers):
    clean = []
    for value in raw_tickers:
        ticker = str(value).upper().replace(".", "-").strip()
        # Remove common annotation fragments seen in historical membership files.
        ticker = ticker.split(" ")[0]
        ticker = ticker.split("(")[0]
        ticker = ticker.strip("-_")
        if ticker and TICKER_PATTERN.match(ticker):
            clean.append(ticker)
    return sorted(set(clean + [config.BENCHMARK_TICKER]))


def load_tickers_from_file(ticker_file=config.TICKER_FILE):
    if not Path(ticker_file).exists():
        raise FileNotFoundError(
            f"Ticker file not found: {ticker_file}. "
            "Create data/tickers.txt or use the default S&P 500 source."
        )

    with open(ticker_file, "r", encoding="utf-8") as handle:
        tickers = [line.strip().upper() for line in handle if line.strip() and not line.strip().startswith("#")]

    if not tickers:
        raise ValueError("Ticker file is empty.")

    return _sanitize_tickers(tickers)


def load_sp500_tickers():
    request = Request(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request) as response:
        html = response.read().decode("utf-8")

    table = pd.read_html(StringIO(html))[0]
    tickers = table["Symbol"].astype(str).tolist()
    return _sanitize_tickers(tickers)


def load_universe_tickers(universe_file=config.UNIVERSE_FILE):
    universe = pd.read_csv(universe_file)
    if "ticker" not in universe.columns:
        raise ValueError("Universe membership file must include a 'ticker' column.")

    tickers = universe["ticker"].astype(str).tolist()
    return _sanitize_tickers(tickers)


def get_tickers(source=DEFAULT_TICKER_SOURCE):
    if source == "file":
        return load_tickers_from_file()
    if source == "membership":
        return load_universe_tickers()
    if source == "sp500":
        return load_sp500_tickers()
    raise ValueError(f"Unsupported ticker source: {source}")


def download_prices(tickers, start=DEFAULT_START_DATE, end=DEFAULT_END_DATE):
    raw = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=True,
        group_by="ticker",
        threads=True,
    )

    if raw.empty:
        raise ValueError("No data returned from yfinance.")

    frames = []

    if isinstance(raw.columns, pd.MultiIndex):
        for ticker in tickers:
            if ticker not in raw.columns.get_level_values(0):
                continue
            ticker_frame = raw[ticker].reset_index()
            ticker_frame["ticker"] = ticker
            frames.append(ticker_frame)
    else:
        ticker = tickers[0]
        ticker_frame = raw.reset_index()
        ticker_frame["ticker"] = ticker
        frames.append(ticker_frame)

    if not frames:
        raise ValueError("Downloaded data could not be reshaped into ticker-level rows.")

    prices = pd.concat(frames, ignore_index=True)
    prices = prices.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )

    required_columns = ["date", "ticker", "open", "close"]
    missing = [column for column in required_columns if column not in prices.columns]
    if missing:
        raise ValueError(f"Missing required columns after download: {missing}")

    prices["date"] = pd.to_datetime(prices["date"]).dt.tz_localize(None)
    prices = prices.sort_values(["ticker", "date"]).reset_index(drop=True)
    return prices


def save_prices(prices, output_file=config.PRICE_FILE):
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output_file, index=False)


def main(source=DEFAULT_TICKER_SOURCE, start=DEFAULT_START_DATE, end=DEFAULT_END_DATE):
    tickers = get_tickers(source=source)
    prices = download_prices(tickers=tickers, start=start, end=end)
    save_prices(prices)

    print(f"Downloaded {prices['ticker'].nunique()} tickers.")
    print(f"Saved data to: {config.PRICE_FILE}")


if __name__ == "__main__":
    main()
