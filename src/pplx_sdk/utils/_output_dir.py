from __future__ import annotations

from pathlib import Path


def resolve_output_root(rd: str | Path | None, *, prefer_pplx_output_dir: bool) -> Path:
    # Public build: no environment-derived output roots.
    return Path(rd) if rd is not None else Path.cwd()
