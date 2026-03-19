from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .elements import (
    BaseElement,
    build_default_element_registry,
    ElementRegistry,
)
from .grid_map import GridMap, Coord


def _parse_key_value_line(line: str) -> Tuple[str, str]:
    """
    Parse `key = value` (spaces around '=' allowed).
    """
    if "=" not in line:
        raise ValueError(f"Invalid metadata line (missing '='): {line!r}")
    key, value = line.split("=", 1)
    return key.strip(), value.strip()


def _tokenize_sandbox_row(row: str) -> List[str]:
    """
    Support both:
    - `# # . x G` (space-separated)
    - `##..xG` (no spaces, one symbol per cell)
    """
    stripped = row.strip()
    if not stripped:
        return []
    parts = stripped.split()
    if len(parts) > 1:
        return parts
    # no spaces -> treat each character as a symbol
    return list(stripped)


def parse_gridmap_file(path: str | Path, element_registry: ElementRegistry | None = None) -> GridMap:
    """
    Parse a `.map` file with structure:
      [Metadata]
      key=value ...

      [Sandbox]
      <rows of symbols>
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    lines = [ln.rstrip("\n") for ln in text.splitlines()]

    section = None
    metadata: Dict[str, str] = {}
    sandbox_rows: List[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip().lower()
            continue
        if section == "metadata":
            k, v = _parse_key_value_line(line)
            metadata[k.lower()] = v
        elif section == "sandbox":
            sandbox_rows.append(raw)
        else:
            raise ValueError(
                f"Unknown/unsupported section or missing section header before line: {raw!r}"
            )

    if "width" not in metadata or "height" not in metadata:
        raise ValueError(f"Missing width/height in metadata of {path}")
    width = int(metadata["width"])
    height = int(metadata["height"])

    reg = element_registry or build_default_element_registry()

    rows_tokens: List[List[str]] = []
    for r in sandbox_rows:
        tokens = _tokenize_sandbox_row(r)
        if tokens:
            rows_tokens.append(tokens)

    if len(rows_tokens) != height:
        raise ValueError(
            f"Sandbox row count mismatch in {path}: expected height={height}, got {len(rows_tokens)}"
        )

    # Build elements for every coordinate.
    elements: Dict[Coord, BaseElement] = {}
    start: Coord | None = None
    goal: Coord | None = None
    start_count = 0
    goal_count = 0

    for y, tokens in enumerate(rows_tokens):
        if len(tokens) != width:
            raise ValueError(
                f"Sandbox row width mismatch in {path} at y={y}: expected width={width}, got {len(tokens)}"
            )
        for x, sym in enumerate(tokens):
            coord = (x, y)
            element_cls = reg.get(sym)
            elements[coord] = element_cls  # store the class for lightweight access
            if element_cls.symbol == "S":
                start = coord
                start_count += 1
            elif element_cls.symbol == "G":
                goal = coord
                goal_count += 1

    if start_count != 1 or goal_count != 1:
        raise ValueError(
            f"Map {path} must contain exactly one S and one G "
            f"(found start_count={start_count}, goal_count={goal_count}, start={start}, goal={goal})"
        )

    return GridMap(
        width=width,
        height=height,
        start=start,
        goal=goal,
        walls=set(),
        elements=elements,
    )

