from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Type, Any


Coord = Tuple[int, int]


@dataclass
class GridMap:
    """
    Minimal 2D grid map representation.
    """

    width: int
    height: int
    start: Coord
    goal: Coord
    walls: Set[Coord]
    # Coordinate -> Element class.
    # Returning the class (not instance) is enough because `numeric_code` and
    # `interact()` are exposed as class-level attributes/methods.
    elements: Dict[Coord, Type[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Import locally to avoid circular imports at module import time.
        from .elements import (
            BaseElement,
            EmptyElement,
            GoalElement,
            StartElement,
            WallElement,
        )

        if self.elements:
            # Build walls set from element passability.
            self.walls = {coord for coord, elem in self.elements.items() if not elem.is_passable()}

            # Make sure start/goal have elements defined.
            if self.start not in self.elements:
                self.elements[self.start] = StartElement
            if self.goal not in self.elements:
                self.elements[self.goal] = GoalElement
            return

        # Legacy/compatibility path: build full element grid from `walls` + start/goal.
        elems: Dict[Coord, Type[BaseElement]] = {}
        for y in range(self.height):
            for x in range(self.width):
                coord = (x, y)
                if coord == self.start:
                    elems[coord] = StartElement
                elif coord == self.goal:
                    elems[coord] = GoalElement
                elif coord in self.walls:
                    elems[coord] = WallElement
                else:
                    elems[coord] = EmptyElement
        self.elements = elems  # type: ignore[assignment]

    def in_bounds(self, pos: Coord) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, pos: Coord) -> bool:
        return pos in self.walls

    def get_element_at(self, x: Coord | int, y: int | None = None) -> Any:
        """
        Global query interface for the Agent/FOV:
          `grid.get_element_at((x, y)).numeric_code`
        """
        # Support both `get_element_at((x, y))` and `get_element_at(x, y)` call styles.
        if y is None:
            if isinstance(x, tuple):
                pos: Coord = x
            else:
                raise ValueError("When y is None, x must be a (x, y) tuple.")
        else:
            if isinstance(x, tuple):
                pos = x  # type: ignore[assignment]
                # If both are provided, only `y` overrides the y-coordinate.
                pos = (pos[0], y)
            else:
                pos = (int(x), y)

        if not self.in_bounds(pos):
            raise ValueError(f"Position out of bounds: {pos}")
        if pos not in self.elements:
            # Should not happen for parsed maps; keep a safe fallback for robustness.
            from .elements import EmptyElement

            self.elements[pos] = EmptyElement
        return self.elements[pos]

    def get_numeric_code_at(self, x: Coord | int, y: int | None = None) -> int:
        elem = self.get_element_at(x, y=y)
        return int(getattr(elem, "numeric_code"))

