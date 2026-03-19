from pathlib import Path

import pandas as pd

from . import config


REQUIRED_COLUMNS = {"ticker", "start_date", "end_date"}


def load_universe_membership(universe_file=None):
    if universe_file is None:
        universe_file = config.UNIVERSE_FILE

    universe_path = Path(universe_file)
    if not universe_path.exists():
        return None

    membership = pd.read_csv(universe_path)
    missing = REQUIRED_COLUMNS - set(membership.columns)
    if missing:
        raise ValueError(f"Universe membership file missing columns: {sorted(missing)}")

    membership = membership.copy()
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.replace(".", "-", regex=False)
    membership["start_date"] = pd.to_datetime(membership["start_date"])
    membership["end_date"] = pd.to_datetime(membership["end_date"])
    membership = membership.sort_values(["ticker", "start_date"]).reset_index(drop=True)
    return membership


def get_eligible_tickers(membership, signal_date):
    if membership is None:
        return None

    signal_date = pd.Timestamp(signal_date)
    if signal_date > pd.Timestamp(membership["end_date"].max()):
        # Membership file can lag recent dates; allow trading the refreshed ticker set for live operation.
        return None

    eligible = membership.loc[
        (membership["start_date"] <= signal_date) & (membership["end_date"] >= signal_date),
        "ticker",
    ]
    return set(eligible.tolist())
