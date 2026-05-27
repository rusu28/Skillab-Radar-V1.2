from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests
from requests import RequestException


class SkillabClient:
    def __init__(
        self,
        api: str,
        username: str,
        password: str,
        cache_dir: str | Path,
        timeout: int = 120,
        pause_seconds: float = 0.15,
        use_cache: bool = True,
        refresh_cache: bool = False,
        retries: int = 3,
    ) -> None:
        self.api = api.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.pause_seconds = pause_seconds
        self.use_cache = use_cache
        self.refresh_cache = refresh_cache
        self.retries = retries
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self._token: str | None = None

    def login(self) -> str:
        if self._token:
            return self._token

        response = self.session.post(
            f"{self.api}/login",
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        self._token = response.text.strip().strip('"')
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.login()}"}

    def _cache_path(self, method: str, endpoint: str, params: dict[str, Any], data: dict[str, Any] | None) -> Path:
        payload = {
            "method": method.upper(),
            "endpoint": endpoint.strip("/"),
            "params": params,
            "data": data or {},
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        safe_endpoint = endpoint.strip("/").replace("/", "__")
        return self.cache_dir / f"{safe_endpoint}_{digest[:20]}.json"

    def request_json(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        params = params or {}
        cache_path = self._cache_path(method, endpoint, params, data)
        if self.use_cache and cache_path.exists() and not self.refresh_cache:
            with cache_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)["response"]

        url = f"{self.api}/{endpoint.strip('/')}"
        last_error: RequestException | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.request(
                    method.upper(),
                    url,
                    headers=self._headers(),
                    params=params,
                    data=data,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                break
            except RequestException as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise
                time.sleep(min(2 * attempt, 10))
        else:
            raise RuntimeError(f"Request failed without response: {last_error}")
        payload = response.json()

        if self.use_cache:
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "request": {"method": method.upper(), "url": url, "params": params, "data": data or {}},
                        "response": payload,
                    },
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
        if self.pause_seconds:
            time.sleep(self.pause_seconds)
        return payload

    def fetch_paged(
        self,
        endpoint: str,
        body: dict[str, Any],
        page_size: int = 300,
        max_pages: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        first = self.request_json("POST", endpoint, params={"page": 1, "page_size": page_size}, data=body)
        count = int(first.get("count", 0))
        items = list(first.get("items", []))
        total_pages = max(1, (count + page_size - 1) // page_size)
        pages_to_fetch = min(total_pages, max_pages) if max_pages else total_pages

        for page in range(2, pages_to_fetch + 1):
            try:
                payload = self.request_json("POST", endpoint, params={"page": page, "page_size": page_size}, data=body)
            except RequestException as exc:
                print(f"Warning: stopping {endpoint} pagination at page {page} after API error: {exc}")
                pages_to_fetch = page - 1
                break
            items.extend(payload.get("items", []))

        provenance = {
            "endpoint": endpoint,
            "request_body": body,
            "api_count": count,
            "page_size": page_size,
            "pages_available": total_pages,
            "pages_fetched": pages_to_fetch,
            "items_fetched": len(items),
        }
        return items, provenance
