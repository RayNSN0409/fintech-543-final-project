from . import config


def build_long_short_weights(
    signal_frame,
    n_long=None,
    n_short=None,
    min_unique=None,
    long_book_weight=None,
    short_book_weight=None,
    excluded_tickers=None,
):
    if n_long is None:
        n_long = config.N_LONG
    if n_short is None:
        n_short = config.N_SHORT
    if min_unique is None:
        min_unique = config.MIN_UNIQUE_SECURITIES
    if long_book_weight is None:
        long_book_weight = config.LONG_BOOK_WEIGHT
    if short_book_weight is None:
        short_book_weight = config.SHORT_BOOK_WEIGHT

    frame = signal_frame.copy()
    excluded = set(excluded_tickers or [])
    if excluded:
        frame = frame.loc[~frame[config.TICKER_COL].isin(excluded)].reset_index(drop=True)

    if frame.empty:
        return {}

    long_candidates = frame.head(n_long)[config.TICKER_COL].tolist()
    short_candidates = frame.tail(n_short)[config.TICKER_COL].tolist()

    long_set = [ticker for ticker in long_candidates if ticker not in short_candidates]
    short_set = [ticker for ticker in short_candidates if ticker not in long_candidates]

    unique_count = len(set(long_set) | set(short_set))
    if unique_count < min_unique:
        return {}

    weights = {}
    if long_set:
        long_weight = float(long_book_weight) / len(long_set)
        for ticker in long_set:
            weights[ticker] = long_weight

    if short_set:
        short_weight = -float(short_book_weight) / len(short_set)
        for ticker in short_set:
            weights[ticker] = short_weight

    return weights
