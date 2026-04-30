"""Student entry point for custom greedy legalization.

The default implementation deliberately returns the input placement unchanged.
Students should replace `legalize()` with their own algorithm.
"""
from __future__ import annotations

from .database.design import Design


def legalize(design: Design) -> Design:
    """Return a legalized design.

    TODO for students:
      1. Assign each movable cell to a legal row.
      2. Snap x coordinates to the row site grid.
      3. Remove all overlaps while minimizing HPWL and displacement.
      4. Keep fixed terminals/macros unchanged.
    """
    return design.copy()
