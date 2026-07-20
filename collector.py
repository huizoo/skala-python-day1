"""외부 API를 비동기로 수집하는 기능을 제공한다."""

import asyncio
from typing import Any

import httpx


async def fetch_json(
    client: httpx.AsyncClient,
    source: str,
    url: str,
) -> tuple[str, dict[str, Any]]:
    """API를 호출하고 출처명과 JSON 응답을 반환한다."""
    response = await client.get(url)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise TypeError(f"{source} 응답이 JSON 객체 형식이 아닙니다.")

    print(f"{source} 수집 완료: HTTP {response.status_code}")

    return source, data


async def collect_all(
    open_meteo_url: str,
    countries_url: str,
    ip_api_url: str,
) -> dict[str, dict[str, Any]]:
    """세 개의 API를 동시에 호출하고 출처별 응답을 반환한다."""
    timeout = httpx.Timeout(20.0)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(
            fetch_json(client, "Open-Meteo", open_meteo_url),
            fetch_json(client, "Countries.dev", countries_url),
            fetch_json(client, "ip-api", ip_api_url),
        )

    return dict(results)
