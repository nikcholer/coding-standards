"""
PR discovery via the GitHub Search Issues API.

The Search API is rate-limited to 30 requests/minute independently of the
core API quota. This module enforces a 2-second floor between page requests
to stay well within that limit.

The Search API also caps results at 1,000 per query. If total_count > 990 for
a given date range, SearchWindowTooLargeError is raised and the caller should
split the date range into monthly sub-queries.
"""
import time
from typing import Iterator

from .client import GitHubClient
from .models import PRRecord


SEARCH_MIN_INTERVAL = 2.1  # seconds between search page requests
SEARCH_RESULT_CAP = 990    # safety margin below the 1,000 hard cap


class SearchWindowTooLargeError(Exception):
    """Raised when a date range returns more than 1,000 results."""
    def __init__(self, total_count: int, date_from: str, date_to: str):
        self.total_count = total_count
        super().__init__(
            f"Search returned {total_count} results for {date_from}..{date_to} "
            f"(cap is {SEARCH_RESULT_CAP}). Split into monthly sub-ranges."
        )


def iter_prs(
    client: GitHubClient,
    repo: str,
    date_from: str,
    date_to: str,
) -> Iterator[PRRecord]:
    """
    Yield PRRecord objects for all merged PRs in the given date range.

    Uses is:merged rather than is:closed to avoid including closed-without-merge
    PRs, which typically lack review discussion.
    """
    query = (
        f"repo:{repo} is:pr is:merged "
        f"created:{date_from}..{date_to}"
    )
    params = {"q": query, "sort": "created", "order": "asc"}

    total_count, items = client.paginate_search("/search/issues", params)

    if total_count > SEARCH_RESULT_CAP:
        raise SearchWindowTooLargeError(total_count, date_from, date_to)

    print(f"Search found {total_count} merged PRs in {date_from}..{date_to}")

    last_request_time = time.monotonic()

    for item in items:
        # Enforce minimum inter-request interval for the search quota.
        # paginate_search fetches pages lazily, so the throttle applies per page.
        elapsed = time.monotonic() - last_request_time
        if elapsed < SEARCH_MIN_INTERVAL:
            time.sleep(SEARCH_MIN_INTERVAL - elapsed)
        last_request_time = time.monotonic()

        yield PRRecord(
            number=item["number"],
            title=item["title"],
            author=item["user"]["login"],
            author_association=item.get("author_association", ""),
            created_at=item["created_at"],
            closed_at=item.get("closed_at"),
            merged_at=None,  # search/issues doesn't include merged_at; omit cleanly
            body=item.get("body"),
        )


def split_monthly(date_from: str, date_to: str) -> list[tuple[str, str]]:
    """
    Return a list of (from, to) monthly sub-ranges covering date_from..date_to.
    Used when a single query exceeds the Search API cap.
    """
    from datetime import date, timedelta
    import calendar

    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    ranges = []
    current = start

    while current <= end:
        _, last_day = calendar.monthrange(current.year, current.month)
        month_end = min(date(current.year, current.month, last_day), end)
        ranges.append((current.isoformat(), month_end.isoformat()))
        current = month_end + timedelta(days=1)

    return ranges
