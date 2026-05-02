from __future__ import annotations

import argparse
import json
from typing import List, Optional

from .metrics import implied_move_from_straddle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilities for earnings-related options studies.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    implied_move = subparsers.add_parser("implied-move", help="Compute ATM straddle implied move.")
    implied_move.add_argument("--spot", type=float, required=True)
    implied_move.add_argument("--call-mid", type=float, required=True)
    implied_move.add_argument("--put-mid", type=float, required=True)
    implied_move.add_argument("--json-indent", type=int, default=2)
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
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
