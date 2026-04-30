from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.database.bookshelf import load_placement, read_bookshelf
from src.database.metrics import check_legality, hpwl


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a placement is legal for a Bookshelf design.")
    parser.add_argument("--aux", type=Path, required=True, help="Path to the Bookshelf .aux file.")
    parser.add_argument("--pl", type=Path, required=True, help="Path to the placement .pl file to check.")
    parser.add_argument("--max-messages", type=int, default=20, help="Maximum number of legality messages to print.")
    parser.add_argument("--json", action="store_true", help="Print the legality report as JSON.")
    args = parser.parse_args()

    try:
        original = read_bookshelf(args.aux.resolve())
        candidate = load_placement(original, args.pl.resolve())
        report = check_legality(candidate, max_messages=args.max_messages)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    payload = report.to_dict()
    payload["design"] = candidate.name
    payload["aux_path"] = str(args.aux.resolve())
    payload["pl_path"] = str(args.pl.resolve())
    payload["hpwl"] = hpwl(candidate)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"design={payload['design']}")
        print(f"placement={payload['pl_path']}")
        print(f"legalized={payload['legalized']}")
        print(f"num_violations={payload['num_violations']}")
        print(f"hpwl={int(round(payload['hpwl']))}")
        if payload["violations"]:
            print("violations:")
            for msg in payload["violations"]:
                print(f"  - {msg}")

    return 0 if report.legalized else 1


if __name__ == "__main__":
    raise SystemExit(main())
