"""
Dataclasses representing the normalised records stored to JSONL.

These align with the EvidenceItem schema defined in the project planning docs.
The GitHub Reviews API (approve/request-changes objects) was introduced in 2016,
so for 2014 data only two comment streams exist: issue comments and review (diff)
comments. The comment_type field distinguishes them.
"""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class PRRecord:
    number: int
    title: str
    author: str
    author_association: str
    created_at: str
    closed_at: Optional[str]
    merged_at: Optional[str]
    body: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IssueCommentRecord:
    pr_number: int
    id: int
    author: str
    author_association: str
    body: str
    created_at: str
    comment_type: str = "issue_comment"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReviewCommentRecord:
    pr_number: int
    id: int
    author: str
    author_association: str
    body: str
    created_at: str
    comment_type: str = "review_comment"
    file_path: Optional[str] = None
    diff_hunk: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)
