from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from options_earnings_lab import event_study_row_from_sdk_chain, select_first_post_event_expiry
from options_earnings_lab import cli as earnings_cli


class _FakeAsset:
    def __init__(self, price: float):
        self.price = price


class _FakeChainRow:
    def __init__(self, payload):
        self._payload = dict(payload)
        self.underlying_asset = _FakeAsset(float(payload["underlying_asset"]["price"]))

    def model_dump(self):
        return dict(self._payload)


class _FakePage:
    def __init__(self, results):
        self.results = list(results)


class _FakeTickers:
    def expirations(self, underlying):
        return _FakePage(["2026-04-24", "2026-04-29", "2026-05-01"])


class _FakeQuotes:
    def list(self, option_symbol, limit=50):
        return _FakePage(
            [
                {"bid_price": 5.0, "ask_price": 5.4},
                {"bid_price": 5.1, "ask_price": 5.5},
            ]
        )


class _FakeOptions:
    def __init__(self, chain_rows):
        self._chain_rows = chain_rows
        self.quotes = _FakeQuotes()

    def chain(self, underlying, expiration_date, limit=250):
        return _FakePage(self._chain_rows)


class _FakeClient:
    def __init__(self):
        rows = [
            _FakeChainRow(
                {
                    "details": {
                        "ticker": "O:MSFT260501C00400000",
                        "contract_type": "call",
                        "expiration_date": "2026-05-01",
                        "strike_price": 400.0,
                    },
                    "last_quote": {"bid": 10.0, "ask": 10.8},
                    "underlying_asset": {"price": 401.0},
                }
            ),
            _FakeChainRow(
                {
                    "details": {
                        "ticker": "O:MSFT260501P00400000",
                        "contract_type": "put",
                        "expiration_date": "2026-05-01",
                        "strike_price": 400.0,
                    },
                    "last_quote": {"bid": 9.8, "ask": 10.4},
                    "underlying_asset": {"price": 401.0},
                }
            ),
        ]
        self.tickers = _FakeTickers()
        self.options = _FakeOptions(rows)

    def close(self):
        return None


def test_select_first_post_event_expiry() -> None:
    assert select_first_post_event_expiry(["2026-04-24", "2026-05-01"], "2026-04-29") == "2026-05-01"


def test_event_study_row_from_sdk_chain() -> None:
    client = _FakeClient()
    result = event_study_row_from_sdk_chain(
        underlying="MSFT",
        event_date="2026-04-29",
        expiry="2026-05-01",
        chain_results=client.options._chain_rows,
        pre_close=395.0,
        post_close=410.0,
    )
    assert result.call_ticker == "O:MSFT260501C00400000"
    assert result.put_ticker == "O:MSFT260501P00400000"
    assert result.implied_move_abs > 0
    assert result.realized_move_pct is not None


def test_event_study_cli_uses_mocked_sdk() -> None:
    with patch.object(earnings_cli, "_load_client_class", return_value=_FakeClient), patch("builtins.print") as print_mock:
        exit_code = earnings_cli.main(
            [
                "event-study",
                "--underlying",
                "MSFT",
                "--event-date",
                "2026-04-29",
                "--pre-close",
                "395",
                "--post-close",
                "410",
                "--include-quote-quality",
            ]
        )
    assert exit_code == 0
    payload = json.loads(print_mock.call_args[0][0])
    assert payload["underlying"] == "MSFT"
    assert payload["call_quote_quality"]["observations"] == 2


def test_batch_event_study_skips_incomplete_rows() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_csv = Path(tmp_dir) / "input.csv"
        output_csv = Path(tmp_dir) / "output.csv"
        with input_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["underlying", "event_date", "pre_close", "post_close"])
            writer.writeheader()
            writer.writerow({"underlying": "MSFT", "event_date": "2026-04-29", "pre_close": "395", "post_close": "410"})
            writer.writerow({"underlying": "", "event_date": "2026-04-29", "pre_close": "395", "post_close": "410"})
        with patch.object(earnings_cli, "_load_client_class", return_value=_FakeClient), patch("builtins.print"):
            exit_code = earnings_cli.main(
                [
                    "batch-event-study",
                    "--input-csv",
                    str(input_csv),
                    "--output-csv",
                    str(output_csv),
                ]
            )
        assert exit_code == 0
        with output_csv.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        assert rows[0]["status"] == "ok"
        assert rows[1]["status"] == "skipped"
