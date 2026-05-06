"""Registry generique par type pour les 4 couches.

Chaque couche (Adapter, Parser, Mapper, Transport) maintient un registry
qui associe un nom de type ("tcp_mllp", "hl7v2", etc.) a une classe
implementant l'interface de cette couche. Les plugins peuvent enregistrer
de nouveaux types sans modifier le coeur.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Registry typed cle -> classe.

    Usage :
        adapter_registry = Registry[BaseAdapter]("adapter")

        @adapter_registry.register("tcp_mllp")
        class TcpMllpAdapter(BaseAdapter):
            ...

        cls = adapter_registry.get("tcp_mllp")
    """

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: dict[str, type[T]] = {}

    def register(self, name: str) -> Callable[[type[T]], type[T]]:
        """Decorateur qui enregistre une classe sous le nom `name`."""

        def decorator(cls: type[T]) -> type[T]:
            if name in self._items:
                raise ValueError(
                    f"{self._kind} '{name}' est deja enregistre par {self._items[name].__name__}"
                )
            self._items[name] = cls
            return cls

        return decorator

    def get(self, name: str) -> type[T]:
        """Recupere la classe enregistree, leve KeyError si inconnue."""
        if name not in self._items:
            raise KeyError(
                f"{self._kind} '{name}' inconnu. Types disponibles : {sorted(self._items)}"
            )
        return self._items[name]

    def names(self) -> list[str]:
        """Liste les noms enregistres, triees."""
        return sorted(self._items)

    def __contains__(self, name: str) -> bool:
        return name in self._items
