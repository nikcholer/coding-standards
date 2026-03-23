"""
Phase 2: Build a prompt for norm extraction from harvested PR comments.

Usage:
    python -m synthesiser

Reads:  data/raw/review_comments.jsonl
        data/raw/issue_comments.jsonl
Writes: data/synthesised/prompt.json   — {system, user} for any LLM API
        data/synthesised/prompt.md     — human-readable version for copy/paste
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path("data/raw")
OUT_DIR = Path("data/synthesised")

SYSTEM_PROMPT = """\
You are an expert engineering standards analyst. Your job is to read a corpus of \
pull request review comments from a software project and extract the implicit \
coding standards that the team's reviewers consistently enforce.

You will be given a list of inline review comments (reviewer, file, and comment body). \
Identify recurring patterns — things reviewers repeatedly ask for or push back on — \
and distil them into a list of candidate coding norms.

For each norm output a JSON object with these fields:
  title            - short label (5-10 words)
  statement        - imperative plain-English rule ("Do X", "Avoid Y")
  rationale        - why the rule exists, inferred from the comments
  category         - one of: architecture / naming / testing / error-handling /
                     security / formatting / documentation / api-design / other
  type             - one of: principle / convention / tooling-rule / preference
  strength         - one of: strong-consensus / moderate / weak-signal / contested
  evidence_count   - approximate number of comments supporting this norm
  example_comments - list of 2-3 short representative quotes (verbatim excerpts)

Return ONLY a JSON array of norm objects. No prose before or after the array.\
"""


def load_comments(path: Path, limit_body: int = 500) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            body = (c.get("body") or "").strip()
            if not body:
                continue
            records.append({
                "pr": c.get("pr_number"),
                "author": c.get("author"),
                "association": c.get("author_association", ""),
                "file": c.get("file_path", ""),
                "body": body[:limit_body],
            })
    return records


def build_user_message(review: list[dict], issue: list[dict]) -> str:
    parts = ["Here is the review comment corpus. Extract the coding norms.\n"]
    if review:
        parts.append(f"## Inline review comments ({len(review)} total)\n")
        for r in review:
            assoc = f" [{r['association']}]" if r["association"] else ""
            file_hint = f" ({r['file']})" if r["file"] else ""
            parts.append(f"- PR#{r['pr']} {r['author']}{assoc}{file_hint}: {r['body']}")
    if issue:
        parts.append(f"\n## General PR thread comments ({len(issue)} total)\n")
        for r in issue:
            assoc = f" [{r['association']}]" if r["association"] else ""
            parts.append(f"- PR#{r['pr']} {r['author']}{assoc}: {r['body']}")
    return "\n".join(parts)


def run():
    review = load_comments(DATA_DIR / "review_comments.jsonl")
    issue = load_comments(DATA_DIR / "issue_comments.jsonl")
    print(f"Loaded {len(review)} review comments, {len(issue)} issue comments.")

    user_message = build_user_message(review, issue)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Machine-readable: {system, user} for any chat-completion API
    json_path = OUT_DIR / "prompt.json"
    json_path.write_text(
        json.dumps({"system": SYSTEM_PROMPT, "user": user_message}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {json_path}")

    # Human-readable markdown for copy/paste
    md_path = OUT_DIR / "prompt.md"
    md_path.write_text(
        f"# Norm Extraction Prompt\n\n"
        f"## System\n\n{SYSTEM_PROMPT}\n\n"
        f"---\n\n"
        f"## User\n\n{user_message}\n",
        encoding="utf-8",
    )
    print(f"Wrote {md_path}")

    # Rough token estimate (chars / 4)
    total_chars = len(SYSTEM_PROMPT) + len(user_message)
    print(f"Estimated prompt size: ~{total_chars // 4:,} tokens")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
