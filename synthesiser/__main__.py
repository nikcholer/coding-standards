"""
Phase 2: Build prompts for norm extraction from harvested PR comments.

Usage:
    python -m synthesiser

Reads:  data/raw/review_comments.jsonl
        data/raw/issue_comments.jsonl
Writes: data/synthesised/norm_extraction_prompt.json  — {system, user} → JSON norms array
        data/synthesised/norm_extraction_prompt.md    — human-readable version
        data/synthesised/register_prompt.json         — {system, user} → human decision register
        data/synthesised/register_prompt.md           — human-readable version
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path("data/raw")
OUT_DIR = Path("data/synthesised")

# Authority tiers for sampling priority
HIGH_AUTHORITY = {"OWNER", "MEMBER"}
MED_AUTHORITY = {"COLLABORATOR"}

# Sample caps: we want a representative but manageable corpus
HIGH_AUTH_CAP = 400   # all high-authority comments up to this
MED_AUTH_CAP = 100    # top medium-authority comments
OTHER_CAP = 100       # small sample of general contributor comments

# ---------------------------------------------------------------------------
# Prompt 1: norm extraction  →  JSON array of norms (machine-processable)
# ---------------------------------------------------------------------------
NORM_EXTRACTION_SYSTEM = """\
You are an expert engineering standards analyst. Your job is to read a corpus of \
pull request review comments from a software project and extract the implicit \
coding standards that the team's reviewers consistently enforce.

You will be given a list of inline review comments (reviewer, authority level, file, \
and comment body). Identify recurring patterns — things reviewers repeatedly ask for \
or push back on — and distil them into a list of candidate coding norms.

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

# ---------------------------------------------------------------------------
# Prompt 2: decision register  →  human-readable markdown document
# ---------------------------------------------------------------------------
REGISTER_SYSTEM = """\
You are an expert engineering standards analyst preparing a decision register for \
senior engineers. Your job is to read a corpus of pull request review comments and \
produce a structured human-readable document that:

1. Identifies candidate coding standards with evidence from the actual comments
2. Assesses the strength of consensus behind each candidate
3. Explicitly flags contradictions or conflicts requiring human decision
4. Notes where a pattern is a personal preference rather than a team norm
5. Recommends whether each candidate should become a rule, a tooling concern, or be dropped

Format your output as a Markdown document with this structure:

---
# Coding Standards Decision Register
## [Repo name] — [date range inferred from comments]

*Generated from [N] review comments. Requires human review and ratification.*

---
## Summary
Brief overview: how many candidates found, how many conflicts, overall signal quality.

---
## Candidate Standards

For each candidate, use this format:

### [Number]. [Title]
**Rule:** [Imperative statement]
**Category:** [category] | **Type:** [principle/convention/tooling-rule/preference] | **Strength:** [strong-consensus/moderate/weak-signal/contested]
**Recommended action:** [Accept as standard / Move to linter / Needs decision / Reject]

**Evidence** (~N comments):
> "[verbatim quote 1]" — @reviewer, PR#nnnn
> "[verbatim quote 2]" — @reviewer, PR#nnnn

**Rationale:** [Why this matters, inferred from the comments]

[If contested, add:] ⚠️ **Conflict:** [Describe the contradiction and who holds each view]

---
## Conflicts Requiring Human Decision
A consolidated list of the items flagged ⚠️ above, with a recommended resolution question \
for each.

---
## Patterns to Move to Tooling
List any norms that belong in a linter/formatter rather than human guidance.

---
## Weak Signals / Insufficient Evidence
Patterns that appeared but lack enough evidence to recommend as standards.\
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


def sample_comments(
    review: list[dict],
    issue: list[dict],
) -> tuple[list[dict], list[dict], dict]:
    """
    Prioritise high-authority comments (OWNER/MEMBER), then medium, then others.
    Returns sampled review list, sampled issue list, and stats dict.
    """
    def tier(c):
        a = c["association"].upper()
        if a in HIGH_AUTHORITY:
            return 0
        if a in MED_AUTHORITY:
            return 1
        return 2

    def sample(comments, caps):
        tiers = [[], [], []]
        for c in comments:
            tiers[tier(c)].append(c)
        result = (
            tiers[0][:caps[0]]
            + tiers[1][:caps[1]]
            + tiers[2][:caps[2]]
        )
        return result, {
            "high_auth_total": len(tiers[0]),
            "med_auth_total": len(tiers[1]),
            "other_total": len(tiers[2]),
            "high_auth_used": min(len(tiers[0]), caps[0]),
            "med_auth_used": min(len(tiers[1]), caps[1]),
            "other_used": min(len(tiers[2]), caps[2]),
        }

    sampled_review, rstats = sample(review, [HIGH_AUTH_CAP, MED_AUTH_CAP, OTHER_CAP])
    # Issue comments: smaller caps, same priority
    sampled_issue, istats = sample(issue, [100, 50, 50])

    stats = {
        "review_total": len(review),
        "review_sampled": len(sampled_review),
        "review_stats": rstats,
        "issue_total": len(issue),
        "issue_sampled": len(sampled_issue),
        "issue_stats": istats,
    }
    return sampled_review, sampled_issue, stats


def build_user_message(review: list[dict], issue: list[dict], stats: dict) -> str:
    parts = [
        f"Here is the review comment corpus "
        f"({stats['review_sampled']} of {stats['review_total']} review comments, "
        f"{stats['issue_sampled']} of {stats['issue_total']} issue comments — "
        f"sampled by reviewer authority).\n"
    ]
    if review:
        parts.append(f"## Inline review comments ({len(review)} total)\n")
        for r in review:
            assoc = f" [{r['association']}]" if r["association"] else ""
            file_hint = f" ({r['file']})" if r["file"] else ""
            parts.append(
                f"- PR#{r['pr']} @{r['author']}{assoc}{file_hint}: {r['body']}"
            )
    if issue:
        parts.append(f"\n## General PR thread comments ({len(issue)} total)\n")
        for r in issue:
            assoc = f" [{r['association']}]" if r["association"] else ""
            parts.append(f"- PR#{r['pr']} @{r['author']}{assoc}: {r['body']}")
    return "\n".join(parts)


def write_prompt(system: str, user: str, stem: str, label: str):
    json_path = OUT_DIR / f"{stem}.json"
    json_path.write_text(
        json.dumps({"system": system, "user": user}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path = OUT_DIR / f"{stem}.md"
    md_path.write_text(
        f"# {label}\n\n"
        f"## System\n\n{system}\n\n"
        f"---\n\n"
        f"## User\n\n{user}\n",
        encoding="utf-8",
    )
    chars = len(system) + len(user)
    print(f"  {json_path}  (~{chars // 4:,} tokens)")
    print(f"  {md_path}")


def run():
    review = load_comments(DATA_DIR / "review_comments.jsonl")
    issue = load_comments(DATA_DIR / "issue_comments.jsonl")
    print(f"Loaded {len(review)} review comments, {len(issue)} issue comments.")

    sampled_review, sampled_issue, stats = sample_comments(review, issue)
    print(
        f"Sampled {stats['review_sampled']} review "
        f"({stats['review_stats']['high_auth_used']} OWNER/MEMBER, "
        f"{stats['review_stats']['med_auth_used']} COLLABORATOR, "
        f"{stats['review_stats']['other_used']} other), "
        f"{stats['issue_sampled']} issue comments."
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    user_message = build_user_message(sampled_review, sampled_issue, stats)

    print("\nWriting norm extraction prompt (-> JSON norms array):")
    write_prompt(
        NORM_EXTRACTION_SYSTEM,
        user_message,
        "norm_extraction_prompt",
        "Norm Extraction Prompt",
    )

    print("\nWriting decision register prompt (-> human-readable markdown):")
    write_prompt(
        REGISTER_SYSTEM,
        user_message,
        "register_prompt",
        "Decision Register Prompt",
    )

    print("\nDone. Send either prompt file to your preferred LLM:")
    print("  register_prompt.json         -> human-reviewable decision document")
    print("  norm_extraction_prompt.json  -> structured JSON for further processing")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
