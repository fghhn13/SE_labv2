from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Type


@dataclass(frozen=True)
class ElementInteractResult:
    """
    Contract between elements and GridWorldEnvironment.

    - terminal: whether the episode should end immediately
    - success: success flag for later evaluation
    - info: extra debug/info fields
    """

    terminal: bool
    success: bool
    info: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "terminal": self.terminal,
            "success": self.success,
            **({} if self.info is None else {"info": self.info}),
        }


class BaseElement:
    """
    Base element definition.
    Elements are intentionally lightweight; GridMap stores them by coordinate.
    """

    symbol: str = "?"
    numeric_code: int = -1
    _is_passable: bool = True

    @classmethod
    def is_passable(cls) -> bool:
        return bool(cls._is_passable)

    @classmethod
    def interact(cls) -> Dict[str, Any]:
        """
        Return a dict like:
          {"terminal": bool, "success": bool, "info": {...}}
        """
        return ElementInteractResult(terminal=False, success=False).to_dict()


class WallElement(BaseElement):
    symbol = "#"
    numeric_code = 1
    _is_passable = False

    @classmethod
    def interact(cls) -> Dict[str, Any]:
        # Walls are non-passable; environment should never call interact() for them.
        return ElementInteractResult(terminal=False, success=False).to_dict()


class EmptyElement(BaseElement):
    symbol = "."
    numeric_code = 0
    _is_passable = True

    @classmethod
    def interact(cls) -> Dict[str, Any]:
        return ElementInteractResult(terminal=False, success=False).to_dict()


class StartElement(BaseElement):
    symbol = "S"
    numeric_code = 2
    _is_passable = True

    @classmethod
    def interact(cls) -> Dict[str, Any]:
        return ElementInteractResult(terminal=False, success=False).to_dict()


class GoalElement(BaseElement):
    symbol = "G"
    numeric_code = 3
    _is_passable = True

    @classmethod
    def interact(cls) -> Dict[str, Any]:
        return ElementInteractResult(terminal=True, success=True).to_dict()


class TrapElement(BaseElement):
    symbol = "x"
    numeric_code = 4
    _is_passable = True

    @classmethod
    def interact(cls) -> Dict[str, Any]:
        # Immediate termination; trap always fails.
        return ElementInteractResult(terminal=True, success=False).to_dict()


class ElementRegistry:
    """
    Symbol -> Element class registry.
    """

    def __init__(self) -> None:
        self._elements: Dict[str, Type[BaseElement]] = {}

    def register(self, element_cls: Type[BaseElement]) -> None:
        symbol = getattr(element_cls, "symbol", None)
        if not symbol:
            raise ValueError("Element class must define non-empty `symbol`.")
        self._elements[symbol] = element_cls

    def get(self, symbol: str) -> Type[BaseElement]:
        if symbol not in self._elements:
            raise ValueError(f"Unknown element symbol: {symbol!r}")
        return self._elements[symbol]

    def try_get(self, symbol: str) -> Type[BaseElement] | None:
        return self._elements.get(symbol)


def build_default_element_registry() -> ElementRegistry:
    reg = ElementRegistry()
    for cls in [WallElement, EmptyElement, StartElement, GoalElement, TrapElement]:
        reg.register(cls)
    return reg

