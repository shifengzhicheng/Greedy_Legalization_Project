"""Command-line runner for baseline/custom legalization and metrics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Optional

from src.database.bookshelf import read_bookshelf, write_pl
from src.database.metrics import collect_metrics
from src.baseline import legalize as baseline_legalize
from src.custom_legalizer import legalize as custom_legalize


PROJECT_ROOT = Path(__file__).resolve().parent


def _find_aux_from_case(case: str, bench_root: Path) -> Path:
    candidates = [bench_root / case, PROJECT_ROOT / "test" / case, PROJECT_ROOT / "test" / "benchmarks" / case]
    for path in candidates:
        if path.is_file() and path.suffix == ".aux":
            return path.resolve()
        if path.is_dir():
            aux_files = sorted(path.glob("*.aux"))
            if aux_files:
                return aux_files[0].resolve()
    raise FileNotFoundError(f"Cannot find .aux for case '{case}' under {bench_root}")


def _format_metric(col: str, value: float) -> str:
    if col in {"original_hpwl", "final_hpwl", "delta_hpwl", "avg_disp_l1", "max_disp_l1"}:
        return str(int(round(value)))
    if col == "delta_hpwl_pct":
        return f"{value:.2f}"
    if col == "runtime_sec":
        return f"{value:.3f}"
    return f"{value:.6f}"


def _print_metrics(metrics: dict) -> None:
    columns = [
        "mode",
        "design",
        "original_hpwl",
        "final_hpwl",
        "delta_hpwl",
        "delta_hpwl_pct",
        "avg_disp_l1",
        "max_disp_l1",
        "runtime_sec",
        "legalized",
        "num_violations",
    ]
    widths = {col: max(len(col), 12) for col in columns}
    values = {}
    for col in columns:
        val = metrics.get(col, "")
        if isinstance(val, float):
            val = _format_metric(col, val)
        else:
            val = str(val)
        values[col] = val
        widths[col] = max(widths[col], len(val))
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    sep = "  ".join("-" * widths[col] for col in columns)
    row = "  ".join(values[col].ljust(widths[col]) for col in columns)
    print(header)
    print(sep)
    print(row)
    if not metrics.get("legalized", False) and metrics.get("violations"):
        print("\nFirst legality messages:")
        for msg in metrics["violations"][:8]:
            print(f"  - {msg}")


def run_one(aux_path: Path, mode: str, out_dir: Path, max_candidate_rows: int = 0) -> dict:
    original = read_bookshelf(aux_path)
    t0 = time.perf_counter()
    if mode == "baseline":
        legalized = baseline_legalize(original, max_candidate_rows=max_candidate_rows)
    elif mode == "custom":
        legalized = custom_legalize(original)
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    runtime = time.perf_counter() - t0

    mode_dir = out_dir / original.name / mode
    pl_path = mode_dir / f"{original.name}.{mode}.pl"
    write_pl(legalized, pl_path)

    metrics = collect_metrics(original, legalized, runtime)
    metrics["mode"] = mode
    metrics["aux_path"] = str(aux_path)
    metrics["output_pl"] = str(pl_path)

    json_path = mode_dir / "metrics.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics["metrics_json"] = str(json_path)
    return metrics


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Bookshelf greedy legalization baseline/custom modes.")
    src = parser.add_mutually_exclusive_group(required=False)
    src.add_argument("--aux", type=Path, help="Path to a Bookshelf .aux file.")
    src.add_argument("--case", type=str, help="Case name under test/benchmarks, e.g. AES/JPEG/GCD/toy_tiny.")
    parser.add_argument("--bench-root", type=Path, default=PROJECT_ROOT / "test" / "benchmarks", help="Benchmark root directory.")
    parser.add_argument("--mode", choices=["baseline", "custom"], required=True, help="Which legalizer to run.")
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "results", help="Output directory for .pl and metrics.json.")
    parser.add_argument("--max-candidate-rows", type=int, default=0, help="Baseline only: 0 tries all rows; N tries closest N rows.")
    args = parser.parse_args(argv)

    try:
        aux_path = args.aux.resolve() if args.aux else _find_aux_from_case(args.case or "toy_tiny", args.bench_root.resolve())
        metrics = run_one(aux_path, args.mode, args.out_dir.resolve(), max_candidate_rows=args.max_candidate_rows)
    except Exception as exc:  # Keep CLI friendly for students.
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.mode == "baseline":
            print(
                "Baseline mode uses the repo's own Design database plus compiled greedy/abacus ops. "
                "If the baseline extensions are missing, build them with CMake under 'src/baseline' or from the repo root.",
                file=sys.stderr,
            )
        return 2

    _print_metrics(metrics)
    print(f"\nOutput placement: {metrics['output_pl']}")
    print(f"Metrics JSON: {metrics['metrics_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
