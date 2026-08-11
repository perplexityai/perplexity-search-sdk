from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

T = TypeVar("T")


def _get_field(hit: Any, name: str) -> Any:  # noqa: ANN401
    if isinstance(hit, dict):
        return hit.get(name)
    return getattr(hit, name, None)


def dedup_by_field(hits: Iterable[T], field: str) -> list[T]:
    by_field: dict[Any, T] = {}
    for hit in hits:
        value = _get_field(hit, field)
        if not value:
            continue
        if value not in by_field:
            by_field[value] = hit
    return list(by_field.values())


def dedup_by_url(hits: Iterable[T]) -> list[T]:
    return dedup_by_field(hits, "url")
