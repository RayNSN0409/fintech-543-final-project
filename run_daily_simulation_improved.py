import argparse

from run_daily_simulation import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run improved diversified daily simulation update."
    )
    parser.add_argument("--force-weekly-report", action="store_true")
    parser.add_argument("--no-refresh-data", action="store_true")
    parser.add_argument("--no-refresh-membership", action="store_true")
    parser.add_argument(
        "--ticker-source",
        choices=["membership", "sp500", "file"],
        default="sp500",
    )
    parser.add_argument("--strict-membership", action="store_true")
    args = parser.parse_args()

    main(
        force_weekly_report=args.force_weekly_report,
        refresh_data=not args.no_refresh_data,
        ticker_source=args.ticker_source,
        strict_membership=args.strict_membership,
        refresh_membership=not args.no_refresh_membership,
        model_name="improved_diversified",
        result_tag="improved_diversified",
        config_overrides={
            "N_LONG": 30,
            "MIN_UNIQUE_SECURITIES": 20,
        },
    )
