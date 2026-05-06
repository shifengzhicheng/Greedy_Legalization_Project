from pathlib import Path

_build_dir = Path(__file__).resolve().parents[4] / "build" / "baseline_ops" / "greedy_legalize"
if _build_dir.is_dir() and str(_build_dir) not in __path__:
    __path__.append(str(_build_dir))

from .greedy_legalize import GreedyLegalize
