#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
BENCH_ROOT="${BENCH_ROOT:-${ROOT}/test/benchmarks}"
OUT_DIR="${OUT_DIR:-${ROOT}/results}"
mkdir -p "${OUT_DIR}"

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
  echo "[WARN] Baseline ops are not built. Build them with CMake under 'src/baseline' or from the repo root."
fi

if [ "$#" -gt 1 ]; then
  echo "Usage: bash run.sh [CASE]" >&2
  exit 2
fi

if [ "$#" -eq 1 ]; then
  CASE_NAME="$1"
else
  CASE_NAME="$(ROOT="${ROOT}" python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
config = json.loads((root / "configs" / "cases.json").read_text(encoding="utf-8"))
name = config.get("name")
if not name:
    raise SystemExit("configs/cases.json must contain a single 'name'")
print(name)
PY
)"
fi

case_dir="${BENCH_ROOT}/${CASE_NAME}"
if [ ! -d "${case_dir}" ]; then
  echo "[ERROR] Missing case directory ${case_dir}." >&2
  exit 1
fi

aux_path="$(find "${case_dir}" -maxdepth 1 -type f -name "*.aux" | sort | head -n 1 || true)"
if [ -z "${aux_path}" ]; then
  echo "[ERROR] No .aux found under ${case_dir}." >&2
  exit 1
fi

echo ""
echo "============================================================"
echo "Case: ${CASE_NAME}"
echo "AUX : ${aux_path}"
echo "============================================================"

if [ "${BASELINE_AVAILABLE}" -eq 1 ]; then
  python main.py --aux "${aux_path}" --mode baseline --out-dir "${OUT_DIR}"
  echo ""
else
  echo "[INFO] Skipping baseline for ${CASE_NAME}; baseline ops are unavailable."
  echo ""
fi

python main.py --aux "${aux_path}" --mode custom --out-dir "${OUT_DIR}"

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
PY
