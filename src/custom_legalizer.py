"""Student entry point for custom greedy legalization."""
from __future__ import annotations

from .database.design import Design


def legalize(design: Design) -> Design:
    """Return a legalized design.

    Students should implement a legalizer that:
      1. Keeps fixed terminals/macros unchanged.
      2. Assigns every movable cell to a legal row.
      3. Snaps x coordinates to the site grid.
      4. Removes overlaps within each row.
      5. Tries to avoid unnecessary HPWL/displacement increase.

    The reference baseline is provided only for comparison and debugging;
    matching or beating it is not required.
    """
    return design.copy()
