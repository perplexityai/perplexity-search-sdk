# perplexity-search-sdk

Python SDK for the Perplexity Search API: live web search and query-relevant
page snippets. A thin Python wrapper over a compiled core built from
Perplexity-internal source.

## Install

```bash
pip install pplx-srch-sdk
```

CPython 3.12+ on Linux (x86_64, aarch64) and macOS. The import name is
`pplx_sdk`.

## Quick start

Get an API key at [perplexity.ai/account/api](https://www.perplexity.ai/account/api)
and export it as `PERPLEXITY_API_KEY`.

```python
import pplx_sdk

hits = pplx_sdk.search.web("rust async runtimes", limit=5)
for hit in hits:
    print(hit.title, hit.url)

snippets = pplx_sdk.content.snippets(
    query="rust async runtimes",
    urls=[hit.url for hit in hits],
)
for s in snippets:
    print(s.url, s.error or (s.text or "")[:200])
```

An async client with the same surface is available as
`pplx_sdk.AsyncPplxClient`.

## Development

The Python wrapper (`src/pplx_sdk/`) is maintained in this repository; PRs
welcome. `bin/` holds the compiled core, delivered prebuilt by Perplexity's
internal release pipeline — never edited by hand. `pip install .` packs the
host platform's `.so` via `scripts/hatch_build.py`; wheels for any supported platform
build on any host with `PPLX_SDK_PLATFORM=<tag> python -m build --wheel`.

Apache-2.0 — see [LICENSE](LICENSE).
