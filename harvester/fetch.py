"""
Per-PR data fetcher: issue comments and inline review (diff) comments.

Note: The GitHub Pull Request Reviews API (formal approve/request-changes objects)
was introduced in 2016. For the 2014 target period these endpoints would return
empty results, so they are not called here. The two data streams that did exist
in 2014 are:
  - Issue comments  (general PR thread discussion)
  - Pull request review comments  (inline diff/code comments)
"""
from .client import GitHubClient
from .models import IssueCommentRecord, ReviewCommentRecord


def fetch_issue_comments(
    client: GitHubClient, repo: str, pr_number: int
) -> list[IssueCommentRecord]:
    records = []
    for comment in client.paginate(f"/repos/{repo}/issues/{pr_number}/comments"):
        records.append(IssueCommentRecord(
            pr_number=pr_number,
            id=comment["id"],
            author=comment["user"]["login"],
            author_association=comment.get("author_association", ""),
            body=comment.get("body", ""),
            created_at=comment["created_at"],
        ))
    return records


def fetch_review_comments(
    client: GitHubClient, repo: str, pr_number: int
) -> list[ReviewCommentRecord]:
    records = []
    for comment in client.paginate(f"/repos/{repo}/pulls/{pr_number}/comments"):
        # `line` reflects the current-version line number; fall back to
        # `original_line` for comments on deleted/moved lines.
        line = comment.get("line") or comment.get("original_line")
        records.append(ReviewCommentRecord(
            pr_number=pr_number,
            id=comment["id"],
            author=comment["user"]["login"],
            author_association=comment.get("author_association", ""),
            body=comment.get("body", ""),
            created_at=comment["created_at"],
            file_path=comment.get("path"),
            diff_hunk=comment.get("diff_hunk"),
            line=line,
        ))
    return records
