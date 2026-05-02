from __future__ import annotations

from options_earnings_lab import implied_move_from_straddle, midpoint, quote_quality_summary, realized_move_pct


def test_midpoint_handles_missing_values() -> None:
    assert midpoint(None, 1.0) is None
    assert midpoint(1.0, None) is None
    assert midpoint(1.0, 1.4) == 1.2


def test_implied_move_from_straddle() -> None:
    estimate = implied_move_from_straddle(spot=400.0, call_mid=10.0, put_mid=12.0)
    assert estimate.straddle_mid == 22.0
    assert estimate.implied_move_abs == 22.0
    assert estimate.implied_move_pct == 0.055


def test_realized_move_pct() -> None:
    assert realized_move_pct(pre_close=100.0, post_close=104.0) == 0.04


def test_quote_quality_summary() -> None:
    summary = quote_quality_summary(
        [
            {"bid_price": 1.0, "ask_price": 1.1},
            {"bid_price": 1.2, "ask_price": 1.3},
            {"bid_price": 2.0, "ask_price": 2.8},
        ]
    )
    assert summary.observations == 3
    assert summary.usable_observations == 3
    assert summary.usable_under_10pct == 2
    assert summary.median_mid > 0
