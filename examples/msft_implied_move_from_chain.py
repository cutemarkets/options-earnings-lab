"""Estimate MSFT implied move from the listed ATM straddle.

This example uses the CuteMarkets Python SDK. Install it separately:

    pip install cutemarkets
"""

from __future__ import annotations

import os

from options_earnings_lab import implied_move_from_straddle, midpoint, select_atm_pair

from cutemarkets import CuteMarkets


def main() -> None:
    client = CuteMarkets(api_key=os.environ.get("CUTEMARKETS_API_KEY"))
    underlying = os.environ.get("CUTEMARKETS_UNDERLYING", "MSFT")
    event_date = os.environ.get("CUTEMARKETS_EVENT_DATE", "2026-04-29")

    expirations = client.tickers.expirations(underlying).results
    expiry = next(value for value in expirations if value >= event_date)
    chain = client.options.chain(underlying, expiration_date=expiry, limit=250)

    spot = float(chain.results[0].underlying_asset.price)
    pair = select_atm_pair([row.model_dump() for row in chain.results], spot=spot)
    if pair is None:
        raise SystemExit("Could not identify an ATM call/put pair.")

    call_row, put_row = pair
    call_quote = call_row.get("last_quote") or {}
    put_quote = put_row.get("last_quote") or {}
    call_mid = midpoint(call_quote.get("bid"), call_quote.get("ask"))
    put_mid = midpoint(put_quote.get("bid"), put_quote.get("ask"))
    if call_mid is None or put_mid is None:
        raise SystemExit("ATM pair did not contain a complete bid/ask.")

    estimate = implied_move_from_straddle(spot=spot, call_mid=call_mid, put_mid=put_mid)
    print(estimate)
    client.close()


if __name__ == "__main__":
    main()
