from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pplx_sdk.utils.jsonl import read_jsonl, write_jsonl


def _is_valid_key(key: str) -> bool:
    return (
        key not in {"", ".", ".."}
        and Path(key).name == key
        and "\\" not in key
        and "\0" not in key
    )


class Checkpoint:
    """Per-key JSONL fragment storage with atomic writes."""

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)
        self._fragments = self.workspace / "fragments"
        self._fragments.mkdir(parents=True, exist_ok=True)

    def has(self, key: str) -> bool:
        if not _is_valid_key(key):
            return False
        return self._path(key).exists()

    def record(self, key: str, rows: Iterable[Any]) -> int:
        path = self._path(key)
        tmp = path.with_suffix(".jsonl.tmp")
        try:
            count = write_jsonl(tmp, rows)
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        return count

    def read_all(self) -> Iterator[Any]:
        paths = sorted(
            self._fragments.glob("*.jsonl"),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
        )
        for path in paths:
            yield from read_jsonl(path)

    def _path(self, key: str) -> Path:
        if not _is_valid_key(key):
            raise ValueError("checkpoint key must be a file name, not a path")
        return self._fragments / f"{key}.jsonl"
