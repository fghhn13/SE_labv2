from typing import Callable, Dict, Any

from lab.core.interfaces import StructureService


StructureBuilder = Callable[..., StructureService]

_REGISTRY: Dict[str, StructureBuilder] = {}


def register(name: str, builder: StructureBuilder) -> None:
    _REGISTRY[name] = builder


def create(name: str, **kwargs: Any) -> StructureService:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown structure service: {name}")
    return _REGISTRY[name](**kwargs)


def list_structures() -> Dict[str, StructureBuilder]:
    return dict(_REGISTRY)

