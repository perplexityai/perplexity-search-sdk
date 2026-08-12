from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import orjson

from pplx_srch_sdk.utils._output_dir import resolve_output_root

_MISSING = object()
DEFAULT_PREVIEW_LIMIT = 5
DEFAULT_PREVIEW_CHARS = 300
MAX_PREVIEW_RECURSION_DEPTH = 100
TRUNCATED_SUFFIX = "...<truncated>"


def _default(value: Any) -> Any:  # noqa: ANN401
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, BaseException):
        payload: dict[str, Any] = {"type": type(value).__name__, "message": str(value)}
        # Preserve fields exposed by pplx_srch_sdk APIError-like exceptions.
        for attr in ("status_code", "body"):
            attr_value = getattr(value, attr, _MISSING)
            if attr_value is not _MISSING:
                payload[attr] = attr_value
        return payload
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_dumps(value: Any) -> str:  # noqa: ANN401
    return orjson.dumps(
        value,
        default=_default,
        option=orjson.OPT_PASSTHROUGH_DATACLASS,
    ).decode()


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")


def _output_envelope(value: Any) -> dict[str, Any]:  # noqa: ANN401
    if isinstance(value, (list, tuple)):
        return {"results": value, "total": len(value)}
    if isinstance(value, dict):
        return dict(value)
    return {"result": value}


def _preview_value(
    value: Any,  # noqa: ANN401
    *,
    max_chars: int,
    depth: int = 0,
) -> Any:  # noqa: ANN401
    if depth >= MAX_PREVIEW_RECURSION_DEPTH:
        return TRUNCATED_SUFFIX
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}{TRUNCATED_SUFFIX}"
    if isinstance(value, (list, tuple)):
        return [
            _preview_value(item, max_chars=max_chars, depth=depth + 1) for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _preview_value(item, max_chars=max_chars, depth=depth + 1)
            for key, item in value.items()
        }
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _preview_value(_default(value), max_chars=max_chars, depth=depth + 1)


def now_timestamp() -> str:
    """Return a UTC timestamp string safe for output file names."""
    return (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z").replace(":", "-")
    )


def to_jsonl(obj: Any) -> str:  # noqa: ANN401
    if isinstance(obj, (list, tuple)):
        return "\n".join(_json_dumps(item) for item in obj)
    return _json_dumps(obj)


def save_and_print(
    obj: Any,  # noqa: ANN401
    *,
    output_dir: str | Path | None = None,
    timestamp: str | None = None,
) -> None:
    """Save a one-off SDK result to JSON and print it with a ``saved_to`` path."""
    payload = _output_envelope(obj)
    path = output_file_name(
        "pplx_srch_sdk",
        uuid.uuid4().hex[:8],
        rd=output_dir,
        timestamp=timestamp,
        extension="json",
        prefer_pplx_output_dir=True,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dumps(payload), encoding="utf-8")

    stdout_payload = {"saved_to": str(path), **payload}
    # A payload-supplied saved_to must not shadow the generated path.
    stdout_payload["saved_to"] = str(path)
    print(_json_dumps(stdout_payload))


def read_jsonl(path: str | Path, *, limit: int | None = None) -> list[Any]:
    """Read JSONL rows from disk, optionally stopping after ``limit`` rows."""
    if limit is not None:
        _require_non_negative("limit", limit)
    rows: list[Any] = []

    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        if limit == 0:
            return rows
        for line_number, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(orjson.loads(line))
            except orjson.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSONL at {path}:{line_number}: {exc.msg}"
                ) from exc
            if limit is not None and len(rows) >= limit:
                break
    return rows


def preview(value: Any, *, max_chars: int = DEFAULT_PREVIEW_CHARS) -> Any:  # noqa: ANN401
    """Return a JSON-compatible preview with long strings truncated recursively."""
    _require_non_negative("max_chars", max_chars)
    return _preview_value(value, max_chars=max_chars)


def print_preview_jsonl(
    path: str | Path,
    *,
    limit: int = DEFAULT_PREVIEW_LIMIT,
    max_chars: int = DEFAULT_PREVIEW_CHARS,
) -> None:
    """Print a JSONL preview of the first rows in ``path``."""
    _require_non_negative("limit", limit)
    _require_non_negative("max_chars", max_chars)
    preview_text = to_jsonl(
        _preview_value(read_jsonl(path, limit=limit), max_chars=max_chars)
    )
    if preview_text:
        print(preview_text)


def output_file_name(
    use_case: str,
    suffix: str,
    *,
    rd: str | Path | None = None,
    timestamp: str | None = None,
    extension: str = "jsonl",
    prefer_pplx_output_dir: bool = False,
) -> Path:
    """Return an output path with a timestamped file name."""
    root = resolve_output_root(rd, prefer_pplx_output_dir=prefer_pplx_output_dir)
    file_timestamp = timestamp if timestamp is not None else now_timestamp()
    return root / f"{use_case}_{file_timestamp}_{suffix}.{extension}"


def write_jsonl(path: str | Path, rows: Iterable[Any]) -> int:
    """Write one JSON-serializable row per line and return the row count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(_json_dumps(row) + "\n")
            count += 1
    return count
