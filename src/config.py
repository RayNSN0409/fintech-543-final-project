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
REBALANCE_WEEKDAY = 4
TRANSACTION_COST_BPS = 0
INITIAL_CAPITAL = 50_000_000.0

# Signal settings (current production strategy)
MOMENTUM_METHOD = "ewma"
MOMENTUM_SCORE_MODE = "raw"
EWMA_HALFLIFE_DAYS = 3
EWMA_MIN_PERIODS = 10
EWMA_VOL_HALFLIFE_DAYS = 10
EWMA_VOL_MIN_PERIODS = 10
MIN_SIGNAL_PRICE = 5.0

# Portfolio construction: weighted momentum, return-first allocation
N_LONG = 15
N_SHORT = 0
MIN_UNIQUE_SECURITIES = 10
SHORT_BORROW_RATE_ANNUAL = 0.10
LONG_BOOK_WEIGHT = 1.00
SHORT_BOOK_WEIGHT = 0.00

# Optional benchmark-trend-based exposure tilting
USE_BENCHMARK_TREND_SWITCH = False
TREND_LOOKBACK_DAYS = 50
BULL_LONG_BOOK_WEIGHT = 0.75
BULL_SHORT_BOOK_WEIGHT = 0.25
BEAR_LONG_BOOK_WEIGHT = 0.45
BEAR_SHORT_BOOK_WEIGHT = 0.55

# Risk target settings
TARGET_ANNUAL_VOLATILITY = 0.18
VOL_LOOKBACK_DAYS = 20
MAX_GROSS_LEVERAGE = 2.00
TRADING_DAYS_PER_YEAR = 252

# Require at least four weeks of live-like backtest window before presentation
MIN_BACKTEST_TRADING_DAYS = 20

DATE_COL = "date"
TICKER_COL = "ticker"
OPEN_COL = "open"
CLOSE_COL = "close"

BENCHMARK_TICKER = "SPY"
