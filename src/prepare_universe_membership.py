from pathlib import Path

import pandas as pd

from . import config


RAW_MEMBERSHIP_FILE = config.DATA_DIR / "sp500_historical_components_raw.csv"
OUTPUT_MEMBERSHIP_FILE = config.UNIVERSE_FILE


def _normalize_ticker(ticker):
    return str(ticker).strip().upper().replace(".", "-")


def load_raw_components(raw_file=RAW_MEMBERSHIP_FILE):
    raw = pd.read_csv(raw_file)
    expected = {"date", "tickers"}
    missing = expected - set(raw.columns)
    if missing:
        raise ValueError(f"Raw membership file missing columns: {sorted(missing)}")

    raw = raw.copy()
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.sort_values("date").reset_index(drop=True)
    return raw


def build_membership_intervals(raw_components):
    records = []
    active_starts = {}

    snapshots = []
    for row in raw_components.itertuples(index=False):
        tickers = {_normalize_ticker(t) for t in str(row.tickers).split(",") if str(t).strip()}
        snapshots.append((pd.Timestamp(row.date), tickers))

    previous_date = None
    previous_tickers = set()

    for snapshot_date, current_tickers in snapshots:
        added = current_tickers - previous_tickers
        removed = previous_tickers - current_tickers

        for ticker in added:
            active_starts[ticker] = snapshot_date

        for ticker in removed:
            start_date = active_starts.pop(ticker, None)
            if start_date is not None:
                records.append(
                    {
                        "ticker": ticker,
                        "start_date": start_date,
                        "end_date": snapshot_date - pd.Timedelta(days=1),
                    }
                )

        previous_date = snapshot_date
        previous_tickers = current_tickers

    if previous_date is not None:
        for ticker in previous_tickers:
            start_date = active_starts.get(ticker, previous_date)
            records.append(
                {
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": pd.Timestamp(config.END_DATE),
                }
            )

    membership = pd.DataFrame(records).sort_values(["ticker", "start_date"]).reset_index(drop=True)
    return membership


def save_membership(membership, output_file=OUTPUT_MEMBERSHIP_FILE):
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    membership.to_csv(output_file, index=False)


def main():
    raw = load_raw_components()
    membership = build_membership_intervals(raw)
    save_membership(membership)

    print(f"Saved membership file to: {OUTPUT_MEMBERSHIP_FILE}")
    print(f"Tickers covered: {membership['ticker'].nunique()}")
    print(f"Rows written: {len(membership)}")


if __name__ == "__main__":
    main()
