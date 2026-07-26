import asyncio
from collections.abc import Callable

import httpx
from loguru import logger


class ResilientClient:
    """HTTP client with retry, backoff, and rate-limit awareness."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers or {})
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    async def _request_with_retry(
        self,
        method: Callable,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        last_resp: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await method(path, **kwargs)
                if resp.status_code == 429:
                    last_resp = resp
                    retry_after = float(resp.headers.get("Retry-After", self._backoff_base * 2))
                    logger.warning("Rate limited on {}, retry after {:.1f}s", path, retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
                last_exc = e
                if attempt < self._max_retries:
                    delay = self._backoff_base * (2**attempt)
                    logger.warning(
                        "Request {} failed (attempt {}): {}, retrying in {:.1f}s",
                        path,
                        attempt + 1,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
        if last_exc is not None:
            raise last_exc
        # All attempts consumed by rate limiting (429)
        raise httpx.HTTPStatusError(
            f"Rate limited on {path} after {self._max_retries + 1} attempts",
            request=last_resp.request,  # type: ignore[union-attr]
            response=last_resp,  # type: ignore[arg-type]
        )

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry(self._client.get, path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry(self._client.post, path, **kwargs)

    async def close(self) -> None:
        await self._client.aclose()
