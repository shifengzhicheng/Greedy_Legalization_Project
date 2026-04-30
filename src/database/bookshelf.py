"""Minimal Bookshelf parser/writer for legalization assignments.

Supported files: .aux, .nodes, .nets, .pl, .scl, optional .wts is ignored.
The parser intentionally handles the common subset used by ISPD/ICCAD-style
standard-cell placement benchmarks and DREAMPlace Bookshelf outputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
import re

from .design import Design, Net, Node, Pin, Placement, Row


_BOOKSHELF_EXTS = {"nodes", "nets", "pl", "scl", "wts", "shapes", "route"}


def _clean_line(line: str) -> str:
    line = line.strip()
    if not line or line.startswith("#"):
        return ""
    if "#" in line:
        line = line.split("#", 1)[0].strip()
    return line


def _data_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = _clean_line(raw)
            if line:
                yield line


def _parse_aux(aux_path: Path) -> Dict[str, Path]:
    text = aux_path.read_text(encoding="utf-8", errors="ignore")
    # Find tokens that look like Bookshelf component file names.
    matches = re.findall(r"([^\s:]+\.(?:nodes|nets|pl|scl|wts|shapes|route))", text, re.IGNORECASE)
    files: Dict[str, Path] = {}
    for token in matches:
        ext = token.rsplit(".", 1)[1].lower()
        if ext in _BOOKSHELF_EXTS and ext not in files:
            files[ext] = (aux_path.parent / token).resolve()
    required = ["nodes", "nets", "pl", "scl"]
    missing = [ext for ext in required if ext not in files]
    if missing:
        raise ValueError(f"{aux_path} missing component files in .aux: {missing}")
    return files


def _parse_nodes(path: Path) -> tuple[Dict[str, Node], List[str]]:
    nodes: Dict[str, Node] = {}
    order: List[str] = []
    for line in _data_lines(path):
        if line.startswith("UCLA") or line.startswith("NumNodes") or line.startswith("NumTerminals"):
            continue
        toks = line.split()
        if len(toks) < 3:
            continue
        name = toks[0]
        try:
            width = float(toks[1])
            height = float(toks[2])
        except ValueError:
            continue
        terminal_type = ""
        is_terminal = False
        if len(toks) >= 4:
            terminal_candidates = [tok for tok in toks[3:] if tok.lower().startswith("terminal")]
            if terminal_candidates:
                terminal_type = terminal_candidates[0]
                is_terminal = True
        nodes[name] = Node(name=name, width=width, height=height, is_terminal=is_terminal, terminal_type=terminal_type)
        order.append(name)
    return nodes, order


def _parse_pl(path: Path, nodes: Dict[str, Node]) -> Dict[str, Placement]:
    placements: Dict[str, Placement] = {}
    for line in _data_lines(path):
        if line.startswith("UCLA"):
            continue
        toks = line.split()
        if len(toks) < 3:
            continue
        name = toks[0]
        if name not in nodes:
            # Some .pl files contain extra metadata names; ignore them.
            continue
        try:
            x = float(toks[1])
            y = float(toks[2])
        except ValueError:
            continue
        orient = "N"
        if ":" in toks:
            idx = toks.index(":")
            if idx + 1 < len(toks):
                orient = toks[idx + 1]
        fixed = any(tok.upper().startswith("/FIXED") for tok in toks)
        if fixed:
            nodes[name].is_terminal = True
            if not nodes[name].terminal_type:
                nodes[name].terminal_type = "terminal"
        placements[name] = Placement(x=x, y=y, orient=orient, is_fixed=fixed)
    # Make missing placements explicit to avoid KeyError in toy/incomplete cases.
    for name in nodes:
        placements.setdefault(name, Placement(0.0, 0.0, "N", nodes[name].is_terminal))
    return placements


def _parse_pin(line: str) -> Optional[Pin]:
    toks = line.split()
    if not toks:
        return None
    node_name = toks[0]
    direction = toks[1] if len(toks) > 1 and toks[1] != ":" else "B"
    offset_x = 0.0
    offset_y = 0.0
    if ":" in toks:
        idx = toks.index(":")
        if idx + 2 < len(toks):
            try:
                offset_x = float(toks[idx + 1])
                offset_y = float(toks[idx + 2])
            except ValueError:
                offset_x = 0.0
                offset_y = 0.0
    return Pin(node_name=node_name, direction=direction, offset_x=offset_x, offset_y=offset_y)


def _parse_nets(path: Path) -> List[Net]:
    lines = list(_data_lines(path))
    nets: List[Net] = []
    i = 0
    auto_idx = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("UCLA") or line.startswith("NumNets") or line.startswith("NumPins"):
            i += 1
            continue
        if line.startswith("NetDegree"):
            m = re.match(r"NetDegree\s*:\s*(\d+)\s*(\S+)?", line)
            if not m:
                i += 1
                continue
            degree = int(m.group(1))
            name = m.group(2) if m.group(2) else f"net_{auto_idx}"
            auto_idx += 1
            pins: List[Pin] = []
            i += 1
            while i < len(lines) and len(pins) < degree:
                pin = _parse_pin(lines[i])
                if pin is not None:
                    pins.append(pin)
                i += 1
            nets.append(Net(name=name, pins=pins))
            continue
        i += 1
    return nets


def _parse_scl(path: Path) -> List[Row]:
    rows: List[Row] = []
    in_row = False
    row_common = {
        "y": 0.0,
        "height": 0.0,
        "site_width": 1.0,
        "site_spacing": 1.0,
        "site_orient": "N",
        "site_symmetry": "Y",
    }
    row_id = 0
    for line in _data_lines(path):
        if line.startswith("UCLA") or line.startswith("NumRows"):
            continue
        if line.startswith("CoreRow"):
            in_row = True
            row_common = {
                "y": 0.0,
                "height": 0.0,
                "site_width": 1.0,
                "site_spacing": 1.0,
                "site_orient": "N",
                "site_symmetry": "Y",
            }
            continue
        if not in_row:
            continue
        if line.startswith("End"):
            in_row = False
            continue

        def number_after(key: str) -> Optional[float]:
            m = re.search(rf"{key}\s*:\s*([^\s]+)", line)
            if not m:
                return None
            try:
                return float(m.group(1))
            except ValueError:
                return None

        def token_after(key: str) -> Optional[str]:
            m = re.search(rf"{key}\s*:\s*([^\s]+)", line)
            return m.group(1) if m else None

        if line.startswith("Coordinate"):
            value = number_after("Coordinate")
            if value is not None:
                row_common["y"] = value
        elif line.startswith("Height"):
            value = number_after("Height")
            if value is not None:
                row_common["height"] = value
        elif line.startswith("Sitewidth"):
            value = number_after("Sitewidth")
            if value is not None:
                row_common["site_width"] = value
        elif line.startswith("Sitespacing"):
            value = number_after("Sitespacing")
            if value is not None:
                row_common["site_spacing"] = value
        elif line.startswith("Siteorient"):
            value = token_after("Siteorient")
            if value is not None:
                row_common["site_orient"] = value
        elif line.startswith("Sitesymmetry"):
            value = token_after("Sitesymmetry")
            if value is not None:
                row_common["site_symmetry"] = value
        elif line.startswith("SubrowOrigin"):
            x_start = number_after("SubrowOrigin")
            num_sites = number_after("NumSites")
            if x_start is None or num_sites is None:
                continue
            rows.append(
                Row(
                    y=float(row_common["y"]),
                    height=float(row_common["height"]),
                    site_width=float(row_common["site_width"]),
                    site_spacing=float(row_common["site_spacing"]),
                    site_orient=str(row_common["site_orient"]),
                    site_symmetry=str(row_common["site_symmetry"]),
                    x_start=x_start,
                    num_sites=int(num_sites),
                    row_id=row_id,
                )
            )
            row_id += 1
    if not rows:
        raise ValueError(f"No rows parsed from {path}")
    return rows


def read_bookshelf(aux_path: str | Path) -> Design:
    aux_path = Path(aux_path).resolve()
    files = _parse_aux(aux_path)
    nodes, node_order = _parse_nodes(files["nodes"])
    placements = _parse_pl(files["pl"], nodes)
    nets = _parse_nets(files["nets"])
    rows = _parse_scl(files["scl"])
    return Design(
        name=aux_path.stem,
        aux_path=aux_path,
        nodes=nodes,
        placements=placements,
        nets=nets,
        rows=rows,
        node_order=node_order,
        raw_aux_files=files,
    )


def load_placement(design: Design, pl_path: str | Path) -> Design:
    updated = design.copy()
    parsed = _parse_pl(Path(pl_path).resolve(), updated.nodes)
    updated.placements.update(parsed)
    return updated


def _fmt_num(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def write_pl(design: Design, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    order = design.node_order or list(design.nodes)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("UCLA pl 1.0\n")
        f.write("# Generated by Greedy legalization teaching project\n\n")
        for name in order:
            node = design.nodes[name]
            pl = design.placements[name]
            suffix = " /FIXED" if (node.is_terminal or pl.is_fixed) else ""
            f.write(f"{name}\t{_fmt_num(pl.x)}\t{_fmt_num(pl.y)}\t: {pl.orient}{suffix}\n")
    return output_path
