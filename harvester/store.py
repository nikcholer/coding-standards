"""
JSONL persistence and resume-state management.

Three append-only JSONL files store the harvested data:
  prs.jsonl             — one PRRecord per line
  issue_comments.jsonl  — one IssueCommentRecord per line
  review_comments.jsonl — one ReviewCommentRecord per line

.progress tracks which PR numbers have been fully committed to disk.
A PR is added to .progress only after all three streams for that PR have been
flushed. This means a killed process may leave duplicate lines for the last
in-flight PR, but deduplication by `id` in the analysis stage handles that.
"""
import json
from pathlib import Path
from typing import IO


def ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def load_progress(progress_file: Path) -> set[int]:
    """Return set of PR numbers already fully harvested."""
    if not progress_file.exists():
        return set()
    with open(progress_file) as f:
        numbers = set()
        for line in f:
            line = line.strip()
            if line:
                numbers.add(int(line))
    return numbers


def mark_progress(progress_file: Path, pr_number: int) -> None:
    """Append a PR number to the progress file."""
    with open(progress_file, "a") as f:
        f.write(f"{pr_number}\n")


def append_record(file_handle: IO, record: dict) -> None:
    """Write a single record as a JSON line."""
    file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
