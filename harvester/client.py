"""
Rate-limited GitHub REST API client.

Handles two distinct rate-limit regimes:
- Core API: 5,000 req/hr. Checked reactively via X-RateLimit-Remaining after
  each response. Sleeps until X-RateLimit-Reset when remaining <= CORE_LIMIT_THRESHOLD.
- Secondary limits: GitHub enforces concurrency/burst limits and returns 403 or 429
  with a Retry-After header. Handled reactively with a configurable default backoff.

This client does NOT enforce the Search API's 30 req/min proactive throttle —
that is the responsibility of search.py, which knows it is calling the search endpoint.
"""
import time
from typing import Iterator, Any

import requests


CORE_LIMIT_THRESHOLD = 20  # sleep when remaining drops to this value


class GitHubClient:
    BASE = "https://api.github.com"

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        })

    def get(self, url: str, params: dict = None) -> requests.Response:
        """Make a single GET request, sleeping on rate limits as needed."""
        while True:
            resp = self.session.get(url, params=params)

            # Secondary rate limit: 403 with Retry-After, or 429
            if resp.status_code in (403, 429):
                retry_after = int(resp.headers.get("Retry-After", 60))
                # Distinguish a secondary-limit 403 from a real auth failure
                if resp.status_code == 429 or "secondary rate limit" in resp.text.lower():
                    print(f"  Secondary rate limit hit — sleeping {retry_after}s")
                    time.sleep(retry_after + 1)
                    continue
                # Real 403 (bad token, no permission, etc.)
                resp.raise_for_status()

            resp.raise_for_status()

            # Core rate limit: sleep proactively if running low
            remaining = int(resp.headers.get("X-RateLimit-Remaining", 9999))
            if remaining <= CORE_LIMIT_THRESHOLD:
                reset_at = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_at - time.time() + 2, 1)
                print(f"  Core rate limit low ({remaining} remaining) — sleeping {wait:.0f}s")
                time.sleep(wait)

            return resp

    def paginate(self, path: str, params: dict = None) -> Iterator[Any]:
        """
        Yield individual items from a paginated GitHub endpoint.

        Follows Link: <url>; rel="next" headers. For Search API responses
        (which wrap items in {"total_count": N, "items": [...]}) unwraps
        automatically. Returns the raw total_count on the first page via a
        side-channel attribute on the generator — callers that need it should
        use iter_pages() instead.
        """
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url = f"{self.BASE}{path}" if not path.startswith("http") else path
        first_request = True

        while url:
            resp = self.get(url, params=params if first_request else None)
            first_request = False
            data = resp.json()

            if isinstance(data, dict) and "items" in data:
                yield from data["items"]
            else:
                yield from data

            url = resp.links.get("next", {}).get("url")

    def paginate_search(self, path: str, params: dict = None) -> tuple[int, Iterator[Any]]:
        """
        Like paginate() but also returns the total_count from the first page.
        Needed so callers can detect the Search API's 1,000-result cap.
        Returns (total_count, generator).
        """
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url = f"{self.BASE}{path}" if not path.startswith("http") else path

        # Fetch first page to get total_count
        resp = self.get(url, params=params)
        data = resp.json()
        total_count = data.get("total_count", 0)
        items = data.get("items", data)
        next_url = resp.links.get("next", {}).get("url")

        def _generator():
            yield from items
            current_url = next_url
            while current_url:
                r = self.get(current_url)
                d = r.json()
                yield from d.get("items", d)
                current_url = r.links.get("next", {}).get("url")

        return total_count, _generator()
