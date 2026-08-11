"""Generic fan-out primitive over any async callable.

`fanout(fn, specs, concurrency=N)` dispatches `fn(**spec)` for each spec with
a bounded asyncio Semaphore, isolates per-call errors into the returned
result, and echoes the spec back next to each outcome so callers can attach
provenance without inspecting results.

This is the building block underneath `pplx_sdk.search.*_many(...)`. Reach
for it directly when you need fan-out for something that doesn't have a
`_many` wrapper yet — `content.snippets` or your own async function.

Example:

    from pplx_sdk import AsyncPplxClient
    from pplx_sdk.utils import fanout

    async with AsyncPplxClient() as client:
        results = await fanout(
            client.search.web,
            [
                {"query": "python 3.13 release notes", "domains": ["python.org"]},
                {"query": "python 3.13 changelog"},
                {"query": "python 3.13 whats new", "domains": ["docs.python.org"]},
            ],
            concurrency=5,
        )
        for r in results:
            if r.ok:
                print(r.spec["query"], "->", len(r.result), "hits")
            else:
                print(r.spec["query"], "failed:", r.error)

Note on `spec` storage: `fanout` shallow-copies each input spec into the
returned `FanoutResult.spec`. Mutable values like `domains=[...]` are
stored by reference, so don't mutate spec values after dispatch — make
a copy first if you need to.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class FanoutResult(Generic[T]):
    """One outcome from `fanout()`: the input spec paired with result-or-error.

    Exactly one of `result` / `error` is non-None. `spec` is a shallow copy
    of the kwargs dict that was dispatched — callers can rely on it for
    provenance (which query produced which hits) without keeping a parallel
    index into the original input list.
    """

    spec: Mapping[str, Any]
    result: T | None = None
    error: Exception | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly nested representation of this fanout outcome."""
        return {
            "ok": self.ok,
            "spec": dict(self.spec),
            "result": self.result,
            "error": str(self.error) if self.error is not None else None,
        }


def partition(
    items: Iterable[T],
    predicate: Callable[[T], bool],
) -> tuple[list[T], list[T]]:
    """Split items into ``(matches, rest)`` by ``predicate``."""
    matches: list[T] = []
    rest: list[T] = []
    for item in items:
        if predicate(item):
            matches.append(item)
        else:
            rest.append(item)
    return matches, rest


def _flatten_item(spec: Mapping[str, Any], item: Any) -> dict[str, Any]:  # noqa: ANN401
    if isinstance(item, Mapping):
        row = dict(item)
    else:
        to_dict = getattr(item, "to_dict", None)
        row = dict(to_dict()) if callable(to_dict) else {"result": item}
    row["spec"] = dict(spec)
    return row


def flatten_fanout_rows(results: Iterable[FanoutResult[Any]]) -> list[dict[str, Any]]:
    """Flatten successful fanout envelopes into item rows with provenance.

    Lists in ``FanoutResult.result`` emit one row per item. Scalar/page-shaped
    results emit one row. Every emitted row includes top-level ``spec`` so
    downstream artifacts keep the original request parameters.
    """
    rows: list[dict[str, Any]] = []
    for fanout_result in results:
        if not fanout_result.ok:
            raise ValueError(
                "flatten_fanout_rows expects successful FanoutResult rows; "
                "call partition(results, lambda r: r.ok) first and persist errors separately"
            )
        if isinstance(fanout_result.result, (list, tuple)):
            rows.extend(
                _flatten_item(fanout_result.spec, item) for item in fanout_result.result
            )
        else:
            rows.append(_flatten_item(fanout_result.spec, fanout_result.result))
    return rows


async def fanout(
    fn: Callable[..., Awaitable[T]],
    specs: Iterable[Mapping[str, Any]],
    *,
    concurrency: int = 5,
) -> list[FanoutResult[T]]:
    """Run `fn(**spec)` for every spec, bounded by `concurrency`, returning
    results in input order with per-call error isolation.

    Args:
        fn: Any async callable (e.g. `client.search.web`,
            `client.content.snippets`, or your own async function).
        specs: Iterable of kwargs dicts. Each is shallow-copied and dispatched
            as `fn(**spec)`. The copy is echoed back on the corresponding
            `FanoutResult.spec` for provenance.
        concurrency: Maximum simultaneous in-flight calls (default 5).

    Returns:
        `list[FanoutResult]` in the same order as `specs`. A failing call
        yields a `FanoutResult` with `.error` set; other calls proceed
        unaffected.

    Example:
        from pplx_sdk import AsyncPplxClient
        from pplx_sdk.utils import fanout

        async with AsyncPplxClient() as client:
            batches = await fanout(
                client.content.snippets,
                [{"query": QUERY, "urls": chunk} for chunk in URL_CHUNKS],
                concurrency=5,
            )
            for r in batches:
                if r.ok:
                    print(len(r.spec["urls"]), "->", len(r.result), "snippets")
                else:
                    print(r.spec["urls"][0], "failed:", r.error)
    """
    if concurrency < 1:
        raise ValueError(f"concurrency must be >= 1, got {concurrency}")
    sem = asyncio.Semaphore(concurrency)
    norm = [dict(s) for s in specs]

    async def _call_one(spec: dict[str, Any]) -> FanoutResult[T]:
        async with sem:
            try:
                return FanoutResult(spec=spec, result=await fn(**spec))
            except Exception as exc:
                return FanoutResult(spec=spec, error=exc)

    return list(await asyncio.gather(*(_call_one(s) for s in norm)))
