from . import config


def select_top_n(signal_frame, top_n=config.TOP_N):
    return signal_frame.head(top_n)[config.TICKER_COL].tolist()


def target_weights(selected_tickers):
    if not selected_tickers:
        return {}

    weight = 1.0 / len(selected_tickers)
    return {ticker: weight for ticker in selected_tickers}
