# perplexity-search-sdk

Python SDK for the Perplexity Search API: live web search and query-relevant
page snippets. A thin Python wrapper over a compiled core built from
Perplexity-internal source.

## Install

```bash
pip install pplx-srch-sdk
```

CPython 3.12+ on Linux (x86_64, aarch64) and macOS. The import name matches:
`import pplx_srch_sdk`.

## Quick start

Get an API key at [perplexity.ai/account/api](https://www.perplexity.ai/account/api)
and export it as `PERPLEXITY_API_KEY`.

```python
import pplx_srch_sdk

hits = pplx_srch_sdk.search.web("rust async runtimes", limit=5)
for hit in hits:
    print(hit.title, hit.url)

snippets = pplx_srch_sdk.content.snippets(
    query="rust async runtimes",
    urls=[hit.url for hit in hits],
)
for s in snippets:
    print(s.url, s.error or (s.text or "")[:200])
```

An async client with the same surface is available as
`pplx_srch_sdk.AsyncPplxClient`.

## Search filters and token budgets

```python
hits = pplx_srch_sdk.search.web(
    "rust async runtimes",
    published_after_date="3/1/2026",
    published_before_date="3/5/2026",
    updated_after_date="3/1/2026",
    max_tokens=8000,
    max_tokens_per_page=4000,
)
```

Publication and last-updated bounds use `MM/DD/YYYY`; `updated_before_date`
sets an upper last-updated bound. Use `recency_filter="hour"` (or `"day"`,
`"week"`, `"month"`, `"year"`) for relative publication recency instead of
`published_after_date` / `published_before_date`.

`max_tokens` caps total search-result content tokens; `max_tokens_per_page`
caps content tokens per result page. Omit `search_context_size` when passing
explicit token budgets. Inspect `help(pplx_srch_sdk.search.web)` for all
options supported by the installed version.

## Development

The Python wrapper (`src/pplx_srch_sdk/`) is maintained in this repository; PRs
welcome. `bin/` holds the compiled core, delivered prebuilt by Perplexity's
internal release pipeline — never edited by hand. `pip install .` packs the
host platform's `.so` via `scripts/hatch_build.py`; wheels for any supported platform
build on any host with `PPLX_SDK_PLATFORM=<tag> python -m build --wheel`.

Apache-2.0 — see [LICENSE](LICENSE).
