from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class AtmStraddleEstimate:
    call_mid: float
    put_mid: float
    spot: float
    straddle_mid: float
    implied_move_abs: float
    implied_move_pct: float


@dataclass(frozen=True)
class QuoteQualitySummary:
    observations: int
    usable_observations: int
    median_mid: float
    median_spread_pct: float
    usable_under_10pct: int


def midpoint(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    mid = (float(bid) + float(ask)) / 2.0
    if mid <= 0:
        return None
    return mid


def implied_move_from_straddle(*, call_mid: float, put_mid: float, spot: float) -> AtmStraddleEstimate:
    resolved_spot = float(spot)
    if resolved_spot <= 0:
        raise ValueError("spot must be > 0")
    straddle_mid = float(call_mid) + float(put_mid)
    return AtmStraddleEstimate(
        call_mid=float(call_mid),
        put_mid=float(put_mid),
        spot=resolved_spot,
        straddle_mid=straddle_mid,
        implied_move_abs=straddle_mid,
        implied_move_pct=straddle_mid / resolved_spot,
    )


def realized_move_pct(*, pre_close: float, post_close: float) -> float:
    resolved_pre_close = float(pre_close)
    if resolved_pre_close <= 0:
        raise ValueError("pre_close must be > 0")
    return (float(post_close) - resolved_pre_close) / resolved_pre_close


def quote_quality_summary(
    rows: Iterable[Mapping[str, float]],
    *,
    max_usable_spread_pct: float = 0.10,
) -> QuoteQualitySummary:
    mids = []
    spreads = []
    usable = 0
    total = 0
    for row in rows:
        total += 1
        bid = row.get("bid") if "bid" in row else row.get("bid_price")
        ask = row.get("ask") if "ask" in row else row.get("ask_price")
        mid = midpoint(bid, ask)
        if mid is None:
            continue
        spread_pct = (float(ask) - float(bid)) / mid
        mids.append(mid)
        spreads.append(spread_pct)
        if spread_pct <= float(max_usable_spread_pct):
            usable += 1
    if not mids or not spreads:
        return QuoteQualitySummary(
            observations=total,
            usable_observations=0,
            median_mid=0.0,
            median_spread_pct=0.0,
            usable_under_10pct=0,
        )
    return QuoteQualitySummary(
        observations=total,
        usable_observations=len(spreads),
        median_mid=float(median(mids)),
        median_spread_pct=float(median(spreads)),
        usable_under_10pct=usable,
    )


def select_atm_pair(
    contracts: Sequence[Mapping[str, object]],
    *,
    spot: float,
) -> Optional[Tuple[Mapping[str, object], Mapping[str, object]]]:
    calls = []
    puts = []
    for row in contracts:
        details = row.get("details")
        if not isinstance(details, Mapping):
            continue
        strike = details.get("strike_price")
        if strike is None:
            continue
        contract_type = str(details.get("contract_type") or "").lower()
        if contract_type == "call":
            calls.append(row)
        elif contract_type == "put":
            puts.append(row)
    if not calls or not puts:
        return None

    def _strike_distance(row: Mapping[str, object]) -> float:
        details = row.get("details")
        if not isinstance(details, Mapping):
            return float("inf")
        return abs(float(details.get("strike_price") or 0.0) - float(spot))

    calls.sort(key=_strike_distance)
    puts.sort(key=_strike_distance)

    best_call = calls[0]
    call_details = best_call.get("details")
    call_strike = float(call_details.get("strike_price") or 0.0) if isinstance(call_details, Mapping) else 0.0
    same_strike_puts = []
    for row in puts:
        details = row.get("details")
        if isinstance(details, Mapping) and float(details.get("strike_price") or 0.0) == call_strike:
            same_strike_puts.append(row)
    best_put = same_strike_puts[0] if same_strike_puts else puts[0]
    return best_call, best_put
