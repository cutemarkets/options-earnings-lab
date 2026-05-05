from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .metrics import implied_move_from_straddle, midpoint, quote_quality_summary, realized_move_pct, select_atm_pair


@dataclass(frozen=True)
class AtmPairSelection:
    underlying: str
    event_date: str
    expiry: str
    spot: float
    call_ticker: str
    put_ticker: str
    call_mid: float
    put_mid: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventStudyResult:
    underlying: str
    event_date: str
    expiry: str
    spot: float
    call_ticker: str
    put_ticker: str
    call_mid: float
    put_mid: float
    straddle_mid: float
    implied_move_abs: float
    implied_move_pct: float
    realized_move_pct: Optional[float] = None
    call_quote_quality: Optional[Dict[str, Any]] = None
    put_quote_quality: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def select_first_post_event_expiry(expirations: Sequence[str], event_date: str) -> str:
    ordered = sorted(str(value) for value in expirations if str(value).strip())
    for expiry in ordered:
        if expiry >= str(event_date):
            return expiry
    raise ValueError(f"no expiry found on or after event date {event_date}")


def resolve_atm_pair(
    *,
    underlying: str,
    event_date: str,
    expiry: str,
    chain_rows: Sequence[Mapping[str, Any]],
    spot: float,
) -> AtmPairSelection:
    pair = select_atm_pair(chain_rows, spot=float(spot))
    if pair is None:
        raise ValueError("could not identify an ATM call/put pair")
    call_row, put_row = pair
    call_quote = dict(call_row.get("last_quote") or {})
    put_quote = dict(put_row.get("last_quote") or {})
    call_mid = midpoint(call_quote.get("bid"), call_quote.get("ask"))
    put_mid = midpoint(put_quote.get("bid"), put_quote.get("ask"))
    if call_mid is None or put_mid is None:
        raise ValueError("ATM pair did not contain a complete bid/ask")
    call_details = dict(call_row.get("details") or {})
    put_details = dict(put_row.get("details") or {})
    return AtmPairSelection(
        underlying=str(underlying).strip().upper(),
        event_date=str(event_date),
        expiry=str(expiry),
        spot=float(spot),
        call_ticker=str(call_details.get("ticker") or ""),
        put_ticker=str(put_details.get("ticker") or ""),
        call_mid=float(call_mid),
        put_mid=float(put_mid),
    )


def build_event_study_result(
    *,
    pair: AtmPairSelection,
    pre_close: Optional[float] = None,
    post_close: Optional[float] = None,
    call_quote_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    put_quote_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    max_usable_spread_pct: float = 0.10,
) -> EventStudyResult:
    estimate = implied_move_from_straddle(
        spot=float(pair.spot),
        call_mid=float(pair.call_mid),
        put_mid=float(pair.put_mid),
    )
    realized: Optional[float] = None
    if pre_close is not None and post_close is not None:
        realized = realized_move_pct(pre_close=float(pre_close), post_close=float(post_close))
    call_quality = (
        quote_quality_summary(call_quote_rows, max_usable_spread_pct=max_usable_spread_pct).__dict__
        if call_quote_rows is not None
        else None
    )
    put_quality = (
        quote_quality_summary(put_quote_rows, max_usable_spread_pct=max_usable_spread_pct).__dict__
        if put_quote_rows is not None
        else None
    )
    return EventStudyResult(
        underlying=pair.underlying,
        event_date=pair.event_date,
        expiry=pair.expiry,
        spot=float(pair.spot),
        call_ticker=pair.call_ticker,
        put_ticker=pair.put_ticker,
        call_mid=float(pair.call_mid),
        put_mid=float(pair.put_mid),
        straddle_mid=float(estimate.straddle_mid),
        implied_move_abs=float(estimate.implied_move_abs),
        implied_move_pct=float(estimate.implied_move_pct),
        realized_move_pct=realized,
        call_quote_quality=call_quality,
        put_quote_quality=put_quality,
    )


def event_study_row_from_sdk_chain(
    *,
    underlying: str,
    event_date: str,
    expiry: str,
    chain_results: Sequence[Any],
    pre_close: Optional[float] = None,
    post_close: Optional[float] = None,
    call_quote_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    put_quote_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    max_usable_spread_pct: float = 0.10,
) -> EventStudyResult:
    chain_rows = [row.model_dump() if hasattr(row, "model_dump") else dict(row) for row in chain_results]
    if not chain_rows:
        raise ValueError("chain results were empty")
    first_row = chain_results[0]
    if hasattr(first_row, "underlying_asset") and getattr(first_row.underlying_asset, "price", None) is not None:
        spot = float(first_row.underlying_asset.price)
    else:
        raw_underlying = chain_rows[0].get("underlying_asset") or {}
        spot = float(dict(raw_underlying).get("price") or 0.0)
    if spot <= 0.0:
        raise ValueError("chain results did not contain a usable spot price")
    pair = resolve_atm_pair(
        underlying=underlying,
        event_date=event_date,
        expiry=expiry,
        chain_rows=chain_rows,
        spot=spot,
    )
    return build_event_study_result(
        pair=pair,
        pre_close=pre_close,
        post_close=post_close,
        call_quote_rows=call_quote_rows,
        put_quote_rows=put_quote_rows,
        max_usable_spread_pct=max_usable_spread_pct,
    )
