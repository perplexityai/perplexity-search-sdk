"""
Perplexity Search SDK

Python SDK for the Perplexity Search API: web search and query-relevant
page snippets, backed by a Rust core with Python bindings via PyO3.

Sync usage (recommended for scripts / pipelines / REPL):

    >>> import pplx_srch_sdk
    >>> hits = pplx_srch_sdk.search.web("Rust programming", limit=5)
    >>> snippets = pplx_srch_sdk.content.snippets("rust language", [h.url for h in hits])

``search.web`` returns ``list[WebHit]``. ``content.snippets`` returns
``list[SnippetResult]``.

Async usage (explicit concurrency control):

    >>> import asyncio
    >>> from pplx_srch_sdk import AsyncPplxClient
    >>> async def main():
    ...     async with AsyncPplxClient() as client:
    ...         hits = await client.search.web("Rust programming", limit=10)
    ...         print(len(hits), hits[0].url)
    >>> asyncio.run(main())

Authentication: set ``PERPLEXITY_API_KEY``, or pass ``api_key=`` to
``AsyncPplxClient`` as the in-process alternative. The ``PPLX_SDK_BASE_URL`` +
``PPLX_SDK_API_KEY`` pair (must be set together) overrides the env key for
custom endpoints.
"""

from . import utils as utils
from ._sync import _SDK_VERSION, content, search
from .pplx_sdk import (  # type: ignore[import-not-found]
    APIError,
    AsyncContentResource,
    AsyncPplxClient,
    AsyncSearchResource,
    AuthenticationError,
    BadRequestError,
    ConnectError,
    ForbiddenError,
    InternalServerError,
    NotAcceptableError,
    NotFoundError,
    PplxSdkError,
    RateLimitError,
    SnippetResult,
    TimeoutError as TimeoutError,
    ValidationError,
    WebHit,
)

__version__ = _SDK_VERSION

# TimeoutError stays importable but out of __all__: a star-import must not
# shadow builtins.TimeoutError (pinned by tests).
__all__ = [
    "APIError",
    "AsyncContentResource",
    "AsyncPplxClient",
    "AsyncSearchResource",
    "AuthenticationError",
    "BadRequestError",
    "ConnectError",
    "ForbiddenError",
    "InternalServerError",
    "NotAcceptableError",
    "NotFoundError",
    "PplxSdkError",
    "RateLimitError",
    "SnippetResult",
    "ValidationError",
    "WebHit",
    "content",
    "search",
]
