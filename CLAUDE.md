# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This repository is a research and planning project for building a pipeline that mines historical GitHub PR discussions to extract and formalise a company's implicit coding standards into an `agents.md` document suitable for AI coding assistants.

The core idea: instead of writing a greenfield style guide, use actual PR review history to surface what reviewers have historically cared about — then distil that into explicit, actionable standards.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the harvester (set GITHUB_TOKEN first)
export GITHUB_TOKEN=ghp_...
python -m harvester

# Re-running after interruption resumes automatically — already-fetched PRs
# are tracked in data/raw/.progress and skipped.
```

Output lands in `data/raw/` (gitignored):
- `prs.jsonl` — PR metadata
- `issue_comments.jsonl` — general PR thread comments
- `review_comments.jsonl` — inline diff/code comments

## Repository State

Phase 1 (harvester) is built. The `planning/` directory contains research notes from AI assistants on architecture, schema design, and tooling approaches. Downstream analysis (classification, synthesis, agents.md generation) is not yet implemented.

## Planned Architecture

The pipeline is conceptually four phases:

1. **Harvest** — Extract PRs, comments, reviews, inline diff comments, and changed files from GitHub APIs (or GHArchive/BigQuery for bulk historical extraction). GitHub separates PR discussion into three streams: issue comments (general), pull request reviews (approval/state), and pull request review comments (inline diff).

2. **Classify** — Separate style signals from one-off engineering judgements. Tag each comment by category (architecture, naming, testing, error-handling, etc.) and type (principle / convention / tooling-rule / preference / exception).

3. **Synthesise** — Cluster semantically similar statements, score for confidence/consistency, detect contradictions and historical drift, and identify where senior reviewers disagree.

4. **Output** — Produce two artefacts: a human decision register (conflicts, evidence, confidence) and a compact machine-usable `agents.md`.

## Key Schema Definitions

### Norm (the core output unit)

Each extracted standard is represented as a `Norm`:

| Field | Values / Notes |
|---|---|
| `title` | Short label |
| `statement` | Imperative plain-English rule |
| `rationale` | Why the rule exists |
| `category` | architecture / naming / testing / error-handling / security / formatting / etc. |
| `type` | principle / convention / tooling-rule / preference / exception |
| `scope` | business / domain / repository / module / individual |
| `applicability` | all code / new-projects-only / touched-code-only / specific context |
| `enforcement_mode` | linter / formatter / build-ci / code-review / agent-guidance / documentation-only |
| `strength` | strong-consensus / moderate / weak-signal / contested / obsolete |
| `status` | proposed / accepted / rejected / superseded / deprecated |
| `migration_policy` | no-retrofit / opportunistic / touched-code-only / new-projects-only / mandatory |
| `evidence_summary` | Prose summary of why the norm exists |
| `supporting_examples[]` | Evidence items (see below) |
| `conflicting_examples[]` | Same structure, contradictory evidence |
| `related_norm_ids[]` | Links to related norms |
| `human_owner` | Person/group responsible for adjudication |

### EvidenceItem (raw extracted evidence)

| Field | Values / Notes |
|---|---|
| `comment_type` | top-level-pr-comment / review-summary / inline-review-comment / reply-in-thread |
| `disposition` | accepted / rejected / discussed / unresolved / unclear |
| `authority_weight` | maintainer / senior / contributor / unknown |
| `recency_weight` | old / mid / recent |
| Plus: `repository`, `pull_request_number`, `reviewer`, `timestamp`, `body_excerpt`, `file_path`, `line_reference`, `outcome` |

## Planned Deliverables

1. **Review corpus store** — Normalised JSON/DB of PRs, comments, reviews, authors, timestamps
2. **Extracted norm register** — Table of candidate rules with evidence counts, proponents, opponents, confidence
3. **Conflict report** — Explicitly lists contradictory guidance for human resolution
4. **Draft engineering standards** — Human-readable decision document
5. **`agents.md`** — Compact operational policy for coding agents, structured around precedence:
   1. Repository-local config and docs
   2. Formatter, linter, CI requirements
   3. Business-wide engineering principles
   4. Avoid enforcing reviewer preferences as rules
   5. When contested, minimise churn and escalate

## Design Principles to Preserve

- **Scope matters**: a business-wide principle is different from a repo-local convention or an individual reviewer habit. Never conflate them.
- **Migration policy is not optional**: every norm must state whether old code should be retrofitted. Default to `no-retrofit` for acquired codebases.
- **Two outputs, not one**: the human decision register is what gives the agent policy its legitimacy. Don't skip it.
- **Tooling over debate**: formatting, import ordering, and naming casing belong in linters/formatters, not in the agent guidance document.
- **Historical drift is not inconsistency**: if a reviewer's position changed over time, record the timeline — it may represent evolution, not contradiction.

## Data Sources

- **GitHub REST API**: issue comments, pull request reviews, pull request review comments (separate endpoints)
- **GHArchive on Google BigQuery**: bulk historical extraction without API rate limits — query `githubarchive.year.*` or `githubarchive.month.*`, always filter by `repo.name` to avoid scanning the full dataset
- **GraphQL API**: review threads and resolution state
