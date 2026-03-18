from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

PRICE_FILE = DATA_DIR / "prices.csv"
TICKER_FILE = DATA_DIR / "tickers.txt"
UNIVERSE_FILE = DATA_DIR / "universe_membership.csv"

START_DATE = "2020-01-01"
END_DATE = "2023-12-31"
LOOKBACK_DAYS = 10
TOP_N = 30
REBALANCE_WEEKDAY = 2
TRANSACTION_COST_BPS = 10
INITIAL_CAPITAL = 10_000_000.0

DATE_COL = "date"
TICKER_COL = "ticker"
OPEN_COL = "open"
CLOSE_COL = "close"

BENCHMARK_TICKER = "SPY"
