import httpx
import pytest

from src.core.http import ResilientClient


def _response(status_code: int, path: str = "/test", **kwargs) -> httpx.Response:
    request = httpx.Request("GET", f"https://example.com{path}")
    return httpx.Response(status_code, request=request, **kwargs)


@pytest.mark.asyncio
async def test_request_with_retry_retries_after_rate_limit(monkeypatch) -> None:
    client = ResilientClient(base_url="https://example.com", max_retries=2, backoff_base=0.5)
    sleep_calls: list[float] = []
    responses = iter([
        _response(429, headers={"Retry-After": "1.5"}),
        _response(200),
    ])

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    async def fake_method(path: str, **kwargs) -> httpx.Response:
        return next(responses)

    monkeypatch.setattr("src.core.http.asyncio.sleep", fake_sleep)

    try:
        response = await client._request_with_retry(fake_method, "/test")
    finally:
        await client.close()

    assert response.status_code == 200
    assert sleep_calls == [1.5]


@pytest.mark.asyncio
async def test_request_with_retry_retries_server_error_then_succeeds(monkeypatch) -> None:
    client = ResilientClient(base_url="https://example.com", max_retries=2, backoff_base=0.25)
    sleep_calls: list[float] = []
    responses = iter([
        _response(503),
        _response(200),
    ])

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    async def fake_method(path: str, **kwargs) -> httpx.Response:
        return next(responses)

    monkeypatch.setattr("src.core.http.asyncio.sleep", fake_sleep)

    try:
        response = await client._request_with_retry(fake_method, "/test")
    finally:
        await client.close()

    assert response.status_code == 200
    assert sleep_calls == [0.25]


@pytest.mark.asyncio
async def test_request_with_retry_raises_after_retry_budget_exhausted(monkeypatch) -> None:
    client = ResilientClient(base_url="https://example.com", max_retries=2, backoff_base=0.25)
    sleep_calls: list[float] = []
    request = httpx.Request("GET", "https://example.com/test")

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    async def fake_method(path: str, **kwargs) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    monkeypatch.setattr("src.core.http.asyncio.sleep", fake_sleep)

    try:
        with pytest.raises(httpx.ConnectError):
            await client._request_with_retry(fake_method, "/test")
    finally:
        await client.close()

    assert sleep_calls == [0.25, 0.5]


@pytest.mark.asyncio
async def test_request_with_retry_raises_http_error_on_429_exhaustion(monkeypatch) -> None:
    client = ResilientClient(base_url="https://example.com", max_retries=2, backoff_base=0.5)
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    async def fake_method(path: str, **kwargs) -> httpx.Response:
        return _response(429, headers={"Retry-After": "0.1"})

    monkeypatch.setattr("src.core.http.asyncio.sleep", fake_sleep)

    try:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client._request_with_retry(fake_method, "/test")
        assert "Rate limited" in str(exc_info.value)
    finally:
        await client.close()

    assert len(sleep_calls) == 3  # max_retries + 1 attempts, each sleeps on 429