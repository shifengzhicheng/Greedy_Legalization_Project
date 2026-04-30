"""Lightweight in-memory design objects for Bookshelf placement."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import copy


@dataclass
class Node:
    name: str
    width: float
    height: float
    is_terminal: bool = False
    terminal_type: str = ""


@dataclass
class Placement:
    x: float
    y: float
    orient: str = "N"
    is_fixed: bool = False


@dataclass
class Pin:
    node_name: str
    direction: str = "B"
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass
class Net:
    name: str
    pins: List[Pin] = field(default_factory=list)


@dataclass
class Row:
    y: float
    height: float
    site_width: float
    site_spacing: float
    site_orient: str
    site_symmetry: str
    x_start: float
    num_sites: int
    row_id: int = 0

    @property
    def site_pitch(self) -> float:
        return self.site_spacing if self.site_spacing > 0 else self.site_width

    @property
    def x_end(self) -> float:
        return self.x_start + self.num_sites * self.site_pitch


@dataclass
class Design:
    name: str
    aux_path: Optional[Path]
    nodes: Dict[str, Node]
    placements: Dict[str, Placement]
    nets: List[Net]
    rows: List[Row]
    node_order: List[str] = field(default_factory=list)
    raw_aux_files: Dict[str, Path] = field(default_factory=dict)

    def copy(self) -> "Design":
        return copy.deepcopy(self)

    @property
    def movable_names(self) -> List[str]:
        names = self.node_order or list(self.nodes)
        return [
            name for name in names
            if name in self.nodes
            and not self.nodes[name].is_terminal
            and not self.placements.get(name, Placement(0, 0)).is_fixed
        ]

    @property
    def fixed_names(self) -> List[str]:
        names = self.node_order or list(self.nodes)
        return [
            name for name in names
            if name in self.nodes
            and (self.nodes[name].is_terminal or self.placements.get(name, Placement(0, 0)).is_fixed)
        ]

    def uniform_row_height(self, tol: float = 1e-6) -> float:
        if not self.rows:
            raise ValueError("Design has no rows")
        height = self.rows[0].height
        for row in self.rows[1:]:
            if abs(row.height - height) > tol:
                raise ValueError("Baseline requires uniform row height across all rows")
        return height

    def uniform_site_pitch(self, tol: float = 1e-6) -> float:
        if not self.rows:
            raise ValueError("Design has no rows")
        pitch = self.rows[0].site_pitch
        if pitch <= 0:
            raise ValueError("Baseline requires positive row site pitch")
        for row in self.rows[1:]:
            if abs(row.site_pitch - pitch) > tol:
                raise ValueError("Baseline requires uniform site pitch across all rows")
        return pitch

    def assert_single_row_movable_cells(self, tol: float = 1e-6) -> None:
        row_height = self.uniform_row_height(tol=tol)
        for name in self.movable_names:
            node = self.nodes[name]
            if node.height > row_height + tol:
                raise ValueError(
                    f"Baseline only supports single-row movable cells; {name} has height {node.height} but row height is {row_height}"
                )

    def core_bbox(self) -> Tuple[float, float, float, float]:
        if not self.rows:
            return (0.0, 0.0, 0.0, 0.0)
        xl = min(row.x_start for row in self.rows)
        xh = max(row.x_end for row in self.rows)
        yl = min(row.y for row in self.rows)
        yh = max(row.y + row.height for row in self.rows)
        return xl, yl, xh, yh
