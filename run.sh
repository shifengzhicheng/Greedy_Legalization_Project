#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
OUT_DIR="${OUT_DIR:-${ROOT}/results}"
mkdir -p "${OUT_DIR}"

usage() {
  cat <<'EOF'
Usage: bash run.sh [CASE|all] [--clean]

Examples:
  bash run.sh
  bash run.sh AES
  bash run.sh JPEG --clean
  bash run.sh toy_tiny
  bash run.sh all --clean
EOF
}

CASE_NAME=""
CLEAN=0
for arg in "$@"; do
  case "$arg" in
    --clean)
      CLEAN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [ -n "${CASE_NAME}" ]; then
        usage >&2
        exit 2
      fi
      CASE_NAME="$arg"
      ;;
  esac
done

if [ -z "${CASE_NAME}" ]; then
  CASE_NAME="$(ROOT="${ROOT}" python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
config = json.loads((root / "configs" / "cases.json").read_text(encoding="utf-8"))
default_case = config.get("default")
if not default_case:
    raise SystemExit("configs/cases.json must contain 'default'")
print(default_case)
PY
)"
fi

if [ "${CLEAN}" -eq 1 ]; then
  rm -rf "${OUT_DIR}"/*
  mkdir -p "${OUT_DIR}"
fi

BASELINE_AVAILABLE=1
if ! python - <<'PY'
try:
    from src.baseline.ops.greedy_legalize import greedy_legalize
    from src.baseline.ops.abacus_legalize import abacus_legalize
except Exception:
    raise SystemExit(1)
PY
then
  BASELINE_AVAILABLE=0
  echo "[WARN] Reference baseline is unavailable in the current Python environment."
  echo "[WARN] Install Python dependencies with: pip install -r requirements.txt"
  echo "[WARN] Then build baseline ops with CMake from the repo root."
fi

if [ "${CASE_NAME}" = "all" ]; then
  mapfile -t CASES < <(ROOT="${ROOT}" python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
config = json.loads((root / "configs" / "cases.json").read_text(encoding="utf-8"))
for case in config.get("cases", []):
    print(case["name"])
PY
)
  if [ "${#CASES[@]}" -eq 0 ]; then
    echo "[ERROR] No cases configured in configs/cases.json." >&2
    exit 1
  fi
else
  CASES=("${CASE_NAME}")
fi

resolve_aux() {
  local case_name="$1"
  ROOT="${ROOT}" CASE_NAME="${case_name}" python - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
case_name = os.environ["CASE_NAME"]
bench_root = root / "test" / "benchmarks"
candidates = [bench_root / case_name, root / "test" / case_name, root / "test" / "benchmarks" / case_name]
for path in candidates:
    if path.is_file() and path.suffix == ".aux":
        print(path.resolve())
        raise SystemExit(0)
    if path.is_dir():
        aux_files = sorted(path.glob("*.aux"))
        if aux_files:
            print(aux_files[0].resolve())
            raise SystemExit(0)
raise SystemExit(f"Cannot find .aux for case '{case_name}'")
PY
}

run_case() {
  local case_name="$1"
  local aux_path
  aux_path="$(resolve_aux "${case_name}")"

  echo ""
  echo "============================================================"
  echo "Case: ${case_name}"
  echo "AUX : ${aux_path}"
  echo "============================================================"

  if [ "${BASELINE_AVAILABLE}" -eq 1 ]; then
    python main.py --case "${case_name}" --mode baseline --out-dir "${OUT_DIR}"
    echo ""
  else
    echo "[INFO] Skipping baseline for ${case_name}; reference baseline ops are unavailable."
    echo ""
  fi

  python main.py --case "${case_name}" --mode custom --out-dir "${OUT_DIR}"
}

for case_name in "${CASES[@]}"; do
  run_case "${case_name}"
done

OUT_DIR="${OUT_DIR}" python - <<'PY'
import csv
import glob
import json
import os

out_dir = os.environ["OUT_DIR"]
fields = [
    "mode", "design", "original_hpwl", "final_hpwl", "delta_hpwl", "delta_hpwl_pct",
    "avg_disp_l1", "max_disp_l1", "runtime_sec", "legalized", "num_violations", "output_pl"
]
rows = []
for path in sorted(glob.glob(os.path.join(out_dir, "*", "*", "metrics.json"))):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows.append({k: data.get(k, "") for k in fields})

summary_path = os.path.join(out_dir, "summary.csv")
with open(summary_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f"\nSummary CSV: {summary_path}")
print("Summary includes all metrics currently present under results/.")
PY
