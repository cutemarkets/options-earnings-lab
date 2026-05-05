"""Estimate MSFT implied move from the listed ATM straddle.

This example uses the CuteMarkets Python SDK. Install it separately:

    pip install cutemarkets
"""

from __future__ import annotations

import os

from options_earnings_lab import event_study_row_from_sdk_chain, select_first_post_event_expiry

from cutemarkets import CuteMarkets


def main() -> None:
    client = CuteMarkets(api_key=os.environ.get("CUTEMARKETS_API_KEY"))
    underlying = os.environ.get("CUTEMARKETS_UNDERLYING", "MSFT")
    event_date = os.environ.get("CUTEMARKETS_EVENT_DATE", "2026-04-29")

    expirations = client.tickers.expirations(underlying).results
    expiry = select_first_post_event_expiry(expirations, event_date)
    chain = client.options.chain(underlying, expiration_date=expiry, limit=250)
    result = event_study_row_from_sdk_chain(
        underlying=underlying,
        event_date=event_date,
        expiry=expiry,
        chain_results=list(chain.results),
    )
    print(result)
    client.close()


if __name__ == "__main__":
    main()
