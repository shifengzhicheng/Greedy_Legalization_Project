#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "cases.json"
REQUIRED_EXTS = ["aux", "nodes", "nets", "pl", "scl"]
AUX_PATTERN = re.compile(r"([^\s:]+\.(?:nodes|nets|pl|scl|wts|shapes|route))", re.IGNORECASE)


def referenced_files(aux_path: Path) -> list[str]:
    text = aux_path.read_text(encoding="utf-8", errors="ignore")
    return AUX_PATTERN.findall(text)


def file_size_text(path: Path) -> str:
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}{unit}"
        size /= 1024.0
    return f"{size:.1f}GB"


def load_cases() -> tuple[str, list[dict]]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    default_case = config.get("default", "")
    cases = config.get("cases", [])
    if not cases:
        raise ValueError("configs/cases.json must contain a non-empty 'cases' list")
    return default_case, cases


def main() -> int:
    try:
        default_case, cases = load_cases()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    overall_ok = True
    print(f"Configured cases: {', '.join(case['name'] for case in cases)}")
    if default_case:
        print(f"Default case: {default_case}")
    print()

    for case in cases:
        case_name = case["name"]
        aux_path = (PROJECT_ROOT / case["aux"]).resolve()
        case_dir = aux_path.parent
        print(f"[{case_name}]")
        print(f"  directory: {case_dir}")
        if not aux_path.exists():
            overall_ok = False
            print(f"  status: MISSING aux file {aux_path.name}")
            print()
            continue

        missing_required = []
        for ext in REQUIRED_EXTS:
            path = case_dir / f"{case_name}.{ext}"
            if path.exists():
                print(f"  {path.name:<12} OK  {file_size_text(path)}")
            else:
                missing_required.append(path.name)
                overall_ok = False
                print(f"  {path.name:<12} MISSING")

        missing_refs = []
        for token in referenced_files(aux_path):
            ref_path = case_dir / token
            if not ref_path.exists():
                missing_refs.append(token)
                overall_ok = False
        if missing_refs:
            print(f"  aux references missing files: {', '.join(missing_refs)}")
        else:
            print("  aux references: OK")
        print()

    if overall_ok:
        print("All configured benchmark cases look ready.")
        return 0
    print("Some benchmark files are missing or inconsistent.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
