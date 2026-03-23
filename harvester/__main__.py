"""
Entry point: python -m harvester

Run sequence:
1. Load already-completed PR numbers from .progress (enables resume after interruption)
2. Open three JSONL output files in append mode
3. Search for merged PRs in the configured date range
   - If the date range exceeds the Search API 1,000-result cap, split into
     monthly sub-queries automatically
4. For each PR not already in .progress:
   a. Write PR metadata to prs.jsonl
   b. Fetch and write issue comments to issue_comments.jsonl
   c. Fetch and write review comments to review_comments.jsonl
   d. Flush all three file handles
   e. Mark PR as complete in .progress
5. Print a summary

Re-running after interruption safely resumes from where it left off.
"""
import sys
import time

from .config import load_config
from .client import GitHubClient
from .search import iter_prs, split_monthly, SearchWindowTooLargeError
from .fetch import fetch_issue_comments, fetch_review_comments
from .store import (
    ensure_data_dir,
    load_progress,
    mark_progress,
    append_record,
)


def run():
    config = load_config()
    ensure_data_dir(config.data_dir)

    progress = load_progress(config.progress_file)
    if progress:
        print(f"Resuming: {len(progress)} PR(s) already harvested, skipping those.")

    client = GitHubClient(config.github_token)

    # Build list of date-range queries, splitting monthly if needed
    date_ranges = [(config.date_from, config.date_to)]

    # Test the primary range first; if it's too large, swap to monthly splits
    try:
        _test_total, _ = client.paginate_search(
            "/search/issues",
            {
                "q": f"repo:{config.repo} is:pr is:merged "
                     f"created:{config.date_from}..{config.date_to}",
                "per_page": 1,
            },
        )
        if _test_total > 990:
            print(
                f"Total PRs ({_test_total}) exceeds search cap — "
                "splitting into monthly sub-queries."
            )
            date_ranges = split_monthly(config.date_from, config.date_to)
    except Exception as e:
        print(f"Warning: could not pre-check result count: {e}")

    prs_path = config.data_dir / "prs.jsonl"
    ic_path = config.data_dir / "issue_comments.jsonl"
    rc_path = config.data_dir / "review_comments.jsonl"

    total_prs = 0
    total_issue_comments = 0
    total_review_comments = 0
    start_time = time.monotonic()

    with (
        open(prs_path, "a", encoding="utf-8") as prs_f,
        open(ic_path, "a", encoding="utf-8") as ic_f,
        open(rc_path, "a", encoding="utf-8") as rc_f,
    ):
        for date_from, date_to in date_ranges:
            for pr in iter_prs(client, config.repo, date_from, date_to):
                if pr.number in progress:
                    continue

                print(f"  PR #{pr.number}: {pr.title[:70]}")

                # a. PR metadata
                append_record(prs_f, pr.to_dict())

                # b. Issue comments
                issue_comments = fetch_issue_comments(client, config.repo, pr.number)
                for ic in issue_comments:
                    append_record(ic_f, ic.to_dict())

                # c. Review (diff) comments
                review_comments = fetch_review_comments(client, config.repo, pr.number)
                for rc in review_comments:
                    append_record(rc_f, rc.to_dict())

                # d. Flush before marking progress
                prs_f.flush()
                ic_f.flush()
                rc_f.flush()

                # e. Mark complete
                mark_progress(config.progress_file, pr.number)
                progress.add(pr.number)

                total_prs += 1
                total_issue_comments += len(issue_comments)
                total_review_comments += len(review_comments)

    elapsed = time.monotonic() - start_time
    print(
        f"\nDone in {elapsed:.0f}s — "
        f"{total_prs} PRs, "
        f"{total_issue_comments} issue comments, "
        f"{total_review_comments} review comments."
    )
    print(f"Output: {config.data_dir.resolve()}")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupted. Re-run to resume from where it left off.")
        sys.exit(1)
