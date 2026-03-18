# Cross-Sectional Momentum Baseline

This project contains a first-pass baseline for a long-only cross-sectional momentum strategy on a stock universe such as the S&P 500.

## Current baseline assumptions

- Daily data with columns: `date`, `ticker`, `open`, `close`
- 20-trading-day momentum signal
- Rebalance signal generated on Friday close
- Trades executed on the next trading day's open
- Long-only portfolio holding the top 10 stocks
- Equal-weight portfolio construction
- 10 bps transaction cost applied on turnover
- Initial capital of $10,000,000

## Project layout

- `data/prices.csv`: input price data
- `data/tickers.txt`: optional custom ticker universe
- `data/universe_membership.sample.csv`: sample historical universe membership format
- `src/`: reusable strategy modules
- `run_baseline.py`: runs the baseline backtest and saves outputs
- `outputs/`: generated results after running the backtest

## Install packages

```bash
pip install pandas yfinance lxml html5lib matplotlib
```

## Download data

Default behavior downloads the S&P 500 universe from Wikipedia and then pulls price data from Yahoo Finance:

```bash
python -m src.download_data
```

If you want your own universe, edit `data/tickers.txt` and then run:

```bash
python -c "from src.download_data import main; main(source='file')"
```

If you have a historical membership file saved as `data/universe_membership.csv` and want to download prices for all tickers that ever appear in that file:

```bash
python -c "from src.download_data import main; main(source='membership')"
```

If you downloaded the public `sp500_historical_components_raw.csv` file, convert it into interval format with:

```bash
python -m src.prepare_universe_membership
```

## Run the baseline

1. Activate your environment.
2. Download data or place your own data in `data/prices.csv`.
3. Run:

```bash
python run_baseline.py
```

## Notes

- If `data/universe_membership.csv` exists, the backtest will only consider tickers that are active on each signal date.
- The membership file should use three columns: `ticker`, `start_date`, `end_date`.
- Benchmark comparison and filters can be added in the next iteration.
