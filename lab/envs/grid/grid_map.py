from dataclasses import dataclass
from typing import Set, Tuple


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

    def in_bounds(self, pos: Coord) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, pos: Coord) -> bool:
        return pos in self.walls

