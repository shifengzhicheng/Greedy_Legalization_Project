"""Optional reference legalizer based on DREAMPlace greedy + abacus legalization."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Tuple
import os
import sys

from ..database.design import Design


def _import_dreamplace_legalizers():
    last_exc = None
    try:
        from .ops.greedy_legalize import greedy_legalize
        from .ops.abacus_legalize import abacus_legalize
        return greedy_legalize, abacus_legalize
    except Exception as exc:
        last_exc = exc

    repo_root = Path(__file__).resolve().parents[2]
    candidates = []
    env_home = os.environ.get("DREAMPLACE_HOME")
    if env_home:
        candidates.append(Path(env_home).resolve())
    candidates.append(repo_root)

    seen = set()
    for home in candidates:
        if home in seen:
            continue
        seen.add(home)
        source_root = home
        if not (source_root / "dreamplace").is_dir():
            continue
        if str(source_root) not in sys.path:
            sys.path.insert(0, str(source_root))
        try:
            import dreamplace.ops.greedy_legalize as greedy_pkg
            import dreamplace.ops.abacus_legalize as abacus_pkg

            build_root = Path(os.environ.get("DREAMPLACE_BUILD_DIR", source_root / "build"))
            greedy_build = build_root / "dreamplace" / "ops" / "greedy_legalize"
            abacus_build = build_root / "dreamplace" / "ops" / "abacus_legalize"
            if greedy_build.is_dir() and str(greedy_build) not in greedy_pkg.__path__:
                greedy_pkg.__path__.append(str(greedy_build))
            if abacus_build.is_dir() and str(abacus_build) not in abacus_pkg.__path__:
                abacus_pkg.__path__.append(str(abacus_build))

            from dreamplace.ops.greedy_legalize import greedy_legalize
            from dreamplace.ops.abacus_legalize import abacus_legalize
            return greedy_legalize, abacus_legalize
        except Exception as exc:
            last_exc = exc

    raise RuntimeError(
        "Baseline mode requires torch plus compiled baseline ops. Build them with CMake under "
        "'src/baseline' or from the repo root so the shared libraries are generated under build/baseline_ops, "
        "or set DREAMPLACE_HOME/DREAMPLACE_BUILD_DIR for a developer fallback to an external DREAMPlace build."
    ) from last_exc


def _node_groups(design: Design) -> Tuple[list[str], list[str], list[str]]:
    names = design.node_order or list(design.nodes)
    movable = []
    fixed = []
    terminal_nis = []
    for name in names:
        node = design.nodes[name]
        pl = design.placements[name]
        terminal_type = node.terminal_type.lower()
        if terminal_type == "terminal_ni":
            terminal_nis.append(name)
        elif node.is_terminal or pl.is_fixed:
            fixed.append(name)
        else:
            movable.append(name)
    return movable, fixed, terminal_nis


def _pin_weights(design: Design, order: list[str]) -> list[float]:
    counts = Counter()
    for net in design.nets:
        for pin in net.pins:
            if pin.node_name in design.nodes:
                counts[pin.node_name] += 1
    return [float(max(counts.get(name, 0), 1)) for name in order]


def legalize(design: Design) -> Design:
    greedy_legalize, abacus_legalize = _import_dreamplace_legalizers()
    import torch

    if not design.rows:
        return design.copy()

    design.assert_single_row_movable_cells()
    row_height = float(design.uniform_row_height())
    site_width = float(design.uniform_site_pitch())

    movable, fixed, terminal_nis = _node_groups(design)
    order = movable + fixed + terminal_nis
    if not movable:
        return design.copy()

    xs = [float(design.placements[name].x) for name in order]
    ys = [float(design.placements[name].y) for name in order]
    widths = [float(design.nodes[name].width) for name in order]
    heights = [float(design.nodes[name].height) for name in order]
    weights = _pin_weights(design, order)

    xl, yl, xh, yh = design.core_bbox()
    num_nodes = len(order)
    num_movable_nodes = len(movable)
    num_terminal_nis = len(terminal_nis)

    dtype = torch.float32
    init_pos = torch.tensor(xs + ys, dtype=dtype)
    pos = init_pos.clone()
    node_size_x = torch.tensor(widths, dtype=dtype)
    node_size_y = torch.tensor(heights, dtype=dtype)
    node_weights = torch.tensor(weights, dtype=dtype)
    flat_region_boxes = torch.empty((0,), dtype=dtype)
    flat_region_boxes_start = torch.zeros((1,), dtype=torch.int32)
    node2fence_region_map = torch.full((num_nodes,), -1, dtype=torch.int32)

    greedy = greedy_legalize.GreedyLegalize(
        node_size_x=node_size_x,
        node_size_y=node_size_y,
        node_weights=node_weights,
        flat_region_boxes=flat_region_boxes,
        flat_region_boxes_start=flat_region_boxes_start,
        node2fence_region_map=node2fence_region_map,
        xl=float(xl),
        yl=float(yl),
        xh=float(xh),
        yh=float(yh),
        site_width=site_width,
        row_height=row_height,
        num_bins_x=1,
        num_bins_y=64,
        num_movable_nodes=num_movable_nodes,
        num_terminal_NIs=num_terminal_nis,
        num_filler_nodes=0,
    )
    abacus = abacus_legalize.AbacusLegalize(
        node_size_x=node_size_x,
        node_size_y=node_size_y,
        node_weights=node_weights,
        flat_region_boxes=flat_region_boxes,
        flat_region_boxes_start=flat_region_boxes_start,
        node2fence_region_map=node2fence_region_map,
        xl=float(xl),
        yl=float(yl),
        xh=float(xh),
        yh=float(yh),
        site_width=site_width,
        row_height=row_height,
        num_bins_x=1,
        num_bins_y=64,
        num_movable_nodes=num_movable_nodes,
        num_terminal_NIs=num_terminal_nis,
        num_filler_nodes=0,
    )

    greedy_pos = greedy(init_pos, pos).view(2, -1)
    legalized_pos = abacus(init_pos, greedy_pos.reshape(-1)).view(2, -1)

    legalized = design.copy()
    displacement_l1 = {}
    displacement_l2 = {}
    for idx, name in enumerate(movable):
        original_pl = design.placements[name]
        greedy_x = float(greedy_pos[0, idx])
        greedy_y = float(greedy_pos[1, idx])
        final_x = float(legalized_pos[0, idx])
        final_y = float(legalized_pos[1, idx])
        legalized.placements[name].x = final_x
        legalized.placements[name].y = final_y

        greedy_dx = greedy_x - original_pl.x
        greedy_dy = greedy_y - original_pl.y
        abacus_dx = final_x - greedy_x
        abacus_dy = final_y - greedy_y
        displacement_l1[name] = abs(greedy_dx) + abs(greedy_dy) + abs(abacus_dx) + abs(abacus_dy)
        displacement_l2[name] = (
            (greedy_dx * greedy_dx + greedy_dy * greedy_dy) ** 0.5
            + (abacus_dx * abacus_dx + abacus_dy * abacus_dy) ** 0.5
        )

    legalized.reference_path_disp_l1 = displacement_l1
    legalized.reference_path_disp_l2 = displacement_l2
    return legalized
