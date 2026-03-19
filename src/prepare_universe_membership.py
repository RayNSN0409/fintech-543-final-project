from pathlib import Path
import argparse

import pandas as pd

from . import config
from .download_data import load_sp500_tickers


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


def _tickers_to_csv_value(tickers):
    return ",".join(sorted({_normalize_ticker(t) for t in tickers if str(t).strip()}))


def append_live_snapshot(raw_components, snapshot_date=None, live_tickers=None):
    if snapshot_date is None:
        snapshot_date = pd.Timestamp.today().normalize()
    else:
        snapshot_date = pd.Timestamp(snapshot_date).normalize()

    if live_tickers is None:
        live_tickers = load_sp500_tickers()

    tickers_csv = _tickers_to_csv_value(live_tickers)

    updated = raw_components.copy()
    updated["date"] = pd.to_datetime(updated["date"]).dt.normalize()

    snapshot_row = pd.DataFrame([{"date": snapshot_date, "tickers": tickers_csv}])
    updated = pd.concat([updated, snapshot_row], ignore_index=True)
    updated = updated.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return updated


def build_membership_intervals(raw_components, terminal_date=None):
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
        if terminal_date is None:
            terminal_date = previous_date
        terminal_date = max(pd.Timestamp(terminal_date), previous_date)

        for ticker in previous_tickers:
            start_date = active_starts.get(ticker, previous_date)
            records.append(
                {
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": terminal_date,
                }
            )

    membership = pd.DataFrame(records).sort_values(["ticker", "start_date"]).reset_index(drop=True)
    return membership


def save_membership(membership, output_file=OUTPUT_MEMBERSHIP_FILE):
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    membership.to_csv(output_file, index=False)


def save_raw_components(raw_components, raw_file=RAW_MEMBERSHIP_FILE):
    Path(raw_file).parent.mkdir(parents=True, exist_ok=True)
    raw_components.to_csv(raw_file, index=False)


def refresh_membership_files(update_live_snapshot=True, snapshot_date=None):
    raw = load_raw_components()

    if update_live_snapshot:
        raw = append_live_snapshot(raw, snapshot_date=snapshot_date)
        save_raw_components(raw)

    terminal_date = pd.Timestamp(raw["date"].max()).normalize()
    membership = build_membership_intervals(raw, terminal_date=terminal_date)
    save_membership(membership)

    return raw, membership


def main(update_live_snapshot=True):
    raw, membership = refresh_membership_files(update_live_snapshot=update_live_snapshot)

    print(f"Saved membership file to: {OUTPUT_MEMBERSHIP_FILE}")
    print(f"Tickers covered: {membership['ticker'].nunique()}")
    print(f"Rows written: {len(membership)}")
    print(f"Membership max end date: {membership['end_date'].max()}")
    print(f"Raw snapshot max date: {raw['date'].max()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build/update dynamic S&P 500 membership intervals from historical snapshots."
    )
    parser.add_argument(
        "--no-live-snapshot",
        action="store_true",
        help="Skip appending current-day S&P 500 snapshot from Wikipedia.",
    )
    args = parser.parse_args()
    main(update_live_snapshot=not args.no_live_snapshot)
