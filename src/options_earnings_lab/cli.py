from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Type

from .event_study import event_study_row_from_sdk_chain, resolve_atm_pair, select_first_post_event_expiry
from .metrics import implied_move_from_straddle


def _load_client_class() -> Type[Any]:
    try:
        from cutemarkets import CuteMarkets
    except ImportError as exc:
        raise SystemExit(
            "This command requires the CuteMarkets Python SDK. Install with "
            "`pip install 'options-earnings-lab[sdk]'` or `pip install cutemarkets-python`."
        ) from exc
    return CuteMarkets


def _json_default(value: Any) -> Any:
    return str(value)


def _quote_rows(client: Any, option_symbol: str, limit: int) -> List[Dict[str, Any]]:
    try:
        page = client.options.quotes.list(option_symbol, limit=max(int(limit), 1))
    except Exception:
        return []
    results = getattr(page, "results", []) or []
    rows: List[Dict[str, Any]] = []
    for row in results:
        rows.append(row.model_dump() if hasattr(row, "model_dump") else dict(row))
    return rows


def _event_study_payload(
    *,
    client: Any,
    underlying: str,
    event_date: str,
    expiry: Optional[str],
    pre_close: Optional[float],
    post_close: Optional[float],
    include_quote_quality: bool,
    quote_limit: int,
    max_usable_spread_pct: float,
) -> Dict[str, Any]:
    expirations = list(client.tickers.expirations(underlying).results or [])
    resolved_expiry = str(expiry or select_first_post_event_expiry(expirations, event_date))
    chain = client.options.chain(underlying, expiration_date=resolved_expiry, limit=250)
    preliminary = event_study_row_from_sdk_chain(
        underlying=underlying,
        event_date=event_date,
        expiry=resolved_expiry,
        chain_results=list(chain.results or []),
        pre_close=pre_close,
        post_close=post_close,
    )
    if not include_quote_quality:
        return preliminary.to_dict()
    call_rows = _quote_rows(client, preliminary.call_ticker, quote_limit)
    put_rows = _quote_rows(client, preliminary.put_ticker, quote_limit)
    enriched = event_study_row_from_sdk_chain(
        underlying=underlying,
        event_date=event_date,
        expiry=resolved_expiry,
        chain_results=list(chain.results or []),
        pre_close=pre_close,
        post_close=post_close,
        call_quote_rows=call_rows,
        put_quote_rows=put_rows,
        max_usable_spread_pct=max_usable_spread_pct,
    )
    return enriched.to_dict()


def _read_batch_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_batch_rows(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(str(key))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value if value is not None else "" for key, value in row.items()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilities for earnings-related options studies.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    implied_move = subparsers.add_parser("implied-move", help="Compute ATM straddle implied move.")
    implied_move.add_argument("--spot", type=float, required=True)
    implied_move.add_argument("--call-mid", type=float, required=True)
    implied_move.add_argument("--put-mid", type=float, required=True)
    implied_move.add_argument("--json-indent", type=int, default=2)

    atm_pair = subparsers.add_parser("atm-pair", help="Resolve the first post-event expiry and ATM call/put pair.")
    atm_pair.add_argument("--underlying", required=True)
    atm_pair.add_argument("--event-date", required=True)
    atm_pair.add_argument("--expiry", default="")
    atm_pair.add_argument("--json-indent", type=int, default=2)

    event_study = subparsers.add_parser("event-study", help="Run a CuteMarkets-backed earnings event study.")
    event_study.add_argument("--underlying", required=True)
    event_study.add_argument("--event-date", required=True)
    event_study.add_argument("--expiry", default="")
    event_study.add_argument("--pre-close", type=float, default=None)
    event_study.add_argument("--post-close", type=float, default=None)
    event_study.add_argument("--include-quote-quality", action="store_true")
    event_study.add_argument("--quote-limit", type=int, default=50)
    event_study.add_argument("--max-usable-spread-pct", type=float, default=0.10)
    event_study.add_argument("--json-indent", type=int, default=2)

    batch = subparsers.add_parser("batch-event-study", help="Run a CSV batch of earnings event studies.")
    batch.add_argument("--input-csv", required=True)
    batch.add_argument("--output-csv", required=True)
    batch.add_argument("--include-quote-quality", action="store_true")
    batch.add_argument("--quote-limit", type=int, default=50)
    batch.add_argument("--max-usable-spread-pct", type=float, default=0.10)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "implied-move":
        estimate = implied_move_from_straddle(
            spot=float(args.spot),
            call_mid=float(args.call_mid),
            put_mid=float(args.put_mid),
        )
        print(json.dumps(estimate.__dict__, indent=int(args.json_indent), sort_keys=True))
        return 0

    if args.command == "atm-pair":
        client = _load_client_class()()
        try:
            underlying = str(args.underlying).strip().upper()
            event_date = str(args.event_date).strip()
            expirations = list(client.tickers.expirations(underlying).results or [])
            resolved_expiry = str(args.expiry).strip() or select_first_post_event_expiry(expirations, event_date)
            chain = client.options.chain(underlying, expiration_date=resolved_expiry, limit=250)
            chain_rows = [row.model_dump() for row in chain.results]
            spot = float(chain.results[0].underlying_asset.price)
            pair = resolve_atm_pair(
                underlying=underlying,
                event_date=event_date,
                expiry=resolved_expiry,
                chain_rows=chain_rows,
                spot=spot,
            )
            print(json.dumps(pair.to_dict(), indent=int(args.json_indent), sort_keys=True, default=_json_default))
            return 0
        finally:
            client.close()

    if args.command == "event-study":
        client = _load_client_class()()
        try:
            payload = _event_study_payload(
                client=client,
                underlying=str(args.underlying).strip().upper(),
                event_date=str(args.event_date).strip(),
                expiry=str(args.expiry).strip() or None,
                pre_close=args.pre_close,
                post_close=args.post_close,
                include_quote_quality=bool(args.include_quote_quality),
                quote_limit=int(args.quote_limit),
                max_usable_spread_pct=float(args.max_usable_spread_pct),
            )
            print(json.dumps(payload, indent=int(args.json_indent), sort_keys=True, default=_json_default))
            return 0
        finally:
            client.close()

    if args.command == "batch-event-study":
        client = _load_client_class()()
        try:
            input_rows = _read_batch_rows(Path(args.input_csv))
            output_rows: List[Dict[str, Any]] = []
            for row in input_rows:
                underlying = str(row.get("underlying") or row.get("ticker") or "").strip().upper()
                event_date = str(row.get("event_date") or "").strip()
                if not underlying or not event_date:
                    output_rows.append(
                        {
                            "underlying": underlying,
                            "event_date": event_date,
                            "status": "skipped",
                            "reason": "missing_underlying_or_event_date",
                        }
                    )
                    continue
                pre_close = row.get("pre_close")
                post_close = row.get("post_close")
                try:
                    payload = _event_study_payload(
                        client=client,
                        underlying=underlying,
                        event_date=event_date,
                        expiry=str(row.get("expiry") or "").strip() or None,
                        pre_close=float(pre_close) if pre_close not in (None, "") else None,
                        post_close=float(post_close) if post_close not in (None, "") else None,
                        include_quote_quality=bool(args.include_quote_quality),
                        quote_limit=int(args.quote_limit),
                        max_usable_spread_pct=float(args.max_usable_spread_pct),
                    )
                    output_rows.append({"status": "ok", **payload})
                except Exception as exc:
                    output_rows.append(
                        {
                            "underlying": underlying,
                            "event_date": event_date,
                            "status": "error",
                            "reason": str(exc),
                        }
                    )
            _write_batch_rows(Path(args.output_csv), output_rows)
            print(json.dumps({"rows": len(output_rows), "output_csv": str(args.output_csv)}, indent=2))
            return 0
        finally:
            client.close()

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
