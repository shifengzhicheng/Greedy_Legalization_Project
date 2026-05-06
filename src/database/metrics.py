"""Placement metrics: HPWL, displacement, and a basic row-based legality checker."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import math

from .design import Design, Row

EPS = 1e-6


@dataclass
class LegalityReport:
    legalized: bool
    num_violations: int
    violations: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _rect(name: str, design: Design) -> Tuple[float, float, float, float]:
    node = design.nodes[name]
    pl = design.placements[name]
    return (pl.x, pl.y, pl.x + node.width, pl.y + node.height)


def rects_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], eps: float = EPS) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if ax1 <= bx0 + eps or bx1 <= ax0 + eps:
        return False
    if ay1 <= by0 + eps or by1 <= ay0 + eps:
        return False
    return True


def hpwl(design: Design) -> float:
    total = 0.0
    for net in design.nets:
        xs: List[float] = []
        ys: List[float] = []
        for pin in net.pins:
            if pin.node_name not in design.nodes or pin.node_name not in design.placements:
                continue
            node = design.nodes[pin.node_name]
            pl = design.placements[pin.node_name]
            # Bookshelf pin offsets are conventionally relative to the node center.
            xs.append(pl.x + 0.5 * node.width + pin.offset_x)
            ys.append(pl.y + 0.5 * node.height + pin.offset_y)
        if len(xs) >= 2:
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return total


def displacement(original: Design, legalized: Design) -> Tuple[float, float, float, float]:
    """Return avg L1, max L1, avg L2, max L2 displacement over movable cells."""
    l1_values: List[float] = []
    l2_values: List[float] = []
    for name in original.movable_names:
        if name not in legalized.placements:
            continue
        a = original.placements[name]
        b = legalized.placements[name]
        dx = b.x - a.x
        dy = b.y - a.y
        l1_values.append(abs(dx) + abs(dy))
        l2_values.append(math.hypot(dx, dy))
    if not l1_values:
        return 0.0, 0.0, 0.0, 0.0
    return (
        sum(l1_values) / len(l1_values),
        max(l1_values),
        sum(l2_values) / len(l2_values),
        max(l2_values),
    )


def _row_matches(design: Design, name: str, tol: float) -> List[Row]:
    node = design.nodes[name]
    pl = design.placements[name]
    return [row for row in design.rows if abs(pl.y - row.y) <= tol and node.height <= row.height + tol]


def _is_snapped(x: float, row: Row, tol: float) -> bool:
    spacing = row.site_spacing if row.site_spacing > 0 else row.site_width
    if spacing <= 0:
        return True
    sites = (x - row.x_start) / spacing
    return abs(sites - round(sites)) <= tol


def check_legality(design: Design, max_messages: int = 30, tol: float = 1e-5) -> LegalityReport:
    violations: List[str] = []
    count = 0

    def add(msg: str) -> None:
        nonlocal count
        count += 1
        if len(violations) < max_messages:
            violations.append(msg)

    row_intervals: Dict[int, List[Tuple[float, float, str]]] = {row.row_id: [] for row in design.rows}

    for name in design.movable_names:
        node = design.nodes[name]
        pl = design.placements[name]
        rows = _row_matches(design, name, tol)
        if not rows:
            add(f"{name}: y={pl.y} does not match a legal row or cell height exceeds row height")
            continue
        containing = [row for row in rows if pl.x >= row.x_start - tol and pl.x + node.width <= row.x_end + tol]
        if not containing:
            add(f"{name}: x-range [{pl.x}, {pl.x + node.width}] is outside legal row span")
            continue
        row = containing[0]
        if not _is_snapped(pl.x, row, tol=1e-4):
            add(f"{name}: x={pl.x} is not snapped to row site grid")
        row_intervals[row.row_id].append((pl.x, pl.x + node.width, name))

    for row_id, intervals in row_intervals.items():
        intervals.sort(key=lambda item: (item[0], item[1], item[2]))
        for prev, curr in zip(intervals, intervals[1:]):
            px0, px1, pn = prev
            cx0, cx1, cn = curr
            if cx0 < px1 - tol:
                add(f"overlap in row {row_id}: {pn} [{px0}, {px1}] vs {cn} [{cx0}, {cx1}]")

    # Check movable-vs-fixed obstacle overlaps. Fixed terminals outside rows simply do not overlap.
    fixed_rects = []
    for fixed_name in design.fixed_names:
        node = design.nodes[fixed_name]
        if node.terminal_type.lower() == "terminal_ni":
            continue
        if node.width <= tol or node.height <= tol:
            continue
        fixed_rects.append((fixed_name, _rect(fixed_name, design)))
    for name in design.movable_names:
        r = _rect(name, design)
        for fixed_name, fr in fixed_rects:
            if rects_overlap(r, fr, tol):
                add(f"{name}: overlaps fixed object {fixed_name}")

    return LegalityReport(legalized=(count == 0), num_violations=count, violations=violations)


def collect_metrics(original: Design, legalized: Design, runtime_sec: float) -> dict:
    original_hpwl = hpwl(original)
    final_hpwl = hpwl(legalized)
    avg_l1, max_l1, avg_l2, max_l2 = displacement(original, legalized)
    legal = check_legality(legalized)
    delta = final_hpwl - original_hpwl
    delta_pct = (delta / original_hpwl * 100.0) if abs(original_hpwl) > EPS else 0.0
    metrics = {
        "design": original.name,
        "num_nodes": len(original.nodes),
        "num_movable": len(original.movable_names),
        "num_fixed": len(original.fixed_names),
        "num_nets": len(original.nets),
        "num_rows": len(original.rows),
        "original_hpwl": original_hpwl,
        "final_hpwl": final_hpwl,
        "delta_hpwl": delta,
        "delta_hpwl_pct": delta_pct,
        "avg_disp_l1": avg_l1,
        "max_disp_l1": max_l1,
        "avg_disp_l2": avg_l2,
        "max_disp_l2": max_l2,
        "runtime_sec": runtime_sec,
        "legalized": legal.legalized,
        "num_violations": legal.num_violations,
        "violations": legal.violations,
    }
    path_l1 = getattr(legalized, "reference_path_disp_l1", None)
    path_l2 = getattr(legalized, "reference_path_disp_l2", None)
    if path_l1 is not None and path_l2 is not None:
        l1_values = [float(path_l1[name]) for name in original.movable_names if name in path_l1]
        l2_values = [float(path_l2[name]) for name in original.movable_names if name in path_l2]
        if l1_values and l2_values:
            metrics.update(
                {
                    "reference_path_avg_disp_l1": sum(l1_values) / len(l1_values),
                    "reference_path_max_disp_l1": max(l1_values),
                    "reference_path_avg_disp_l2": sum(l2_values) / len(l2_values),
                    "reference_path_max_disp_l2": max(l2_values),
                }
            )
    return metrics
