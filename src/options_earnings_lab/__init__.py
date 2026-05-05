"""Research utilities for earnings-related options studies."""

from .event_study import (
    AtmPairSelection,
    EventStudyResult,
    build_event_study_result,
    event_study_row_from_sdk_chain,
    resolve_atm_pair,
    select_first_post_event_expiry,
)
from .metrics import (
    AtmStraddleEstimate,
    QuoteQualitySummary,
    implied_move_from_straddle,
    midpoint,
    quote_quality_summary,
    realized_move_pct,
    select_atm_pair,
)

__all__ = [
    "AtmStraddleEstimate",
    "AtmPairSelection",
    "EventStudyResult",
    "QuoteQualitySummary",
    "build_event_study_result",
    "event_study_row_from_sdk_chain",
    "midpoint",
    "implied_move_from_straddle",
    "realized_move_pct",
    "quote_quality_summary",
    "resolve_atm_pair",
    "select_first_post_event_expiry",
    "select_atm_pair",
]
