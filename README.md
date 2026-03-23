# coding-standards

A pipeline that mines historical GitHub pull request discussions to extract and formalise a team's implicit coding standards — producing both a human decision register and a compact `agents.md` for AI coding assistants.

> **This project was generated entirely by an AI coding agent** from two planning conversations saved in [`planning/`](./planning/). No human wrote any of the implementation code. See [MAKING_OF.md](./MAKING_OF.md) for the full story.

---

## The Problem

Every engineering team has a house style. Most of it is never written down — it lives in PR review comments, in the institutional knowledge of senior reviewers, in the friction of code review. When a new developer joins, or when an AI coding assistant starts contributing, that knowledge is invisible.

The usual answer is to write a style guide from scratch. This project takes a different approach: **excavate the standards your team has already been enforcing**, by reading the actual PR history.

The result is:
- a human-reviewable register of candidate norms, each with evidence and confidence scores
- an explicit conflict report where reviewers have contradicted each other or themselves over time
- a compact `agents.md` that AI coding assistants can use as an operational policy

---

## How It Works

The pipeline has four phases:

```
GitHub PRs  →  Harvest  →  Synthesise  →  [Human review]  →  agents.md
```

### Phase 1 — Harvest `[implemented]`

Pulls merged PRs from a GitHub repository using the REST API, extracting all three comment streams that GitHub separates:
- **Issue comments** — general PR thread discussion
- **Pull request reviews** — approval/rejection summaries
- **Pull request review comments** — inline diff/code comments

Output lands in `data/raw/` as three JSONL files. Resumable after interruption via `.progress`.

### Phase 2 — Synthesise `[implemented]`

Reads the harvested corpus, samples by reviewer authority (prioritising `OWNER`/`MEMBER` comments as the highest-signal evidence), and produces two structured prompts for any reasoning LLM:

- **`register_prompt`** — asks the LLM to produce a human-readable decision register: candidate standards with verbatim evidence quotes, conflict flags, tooling recommendations, and a consolidated list of items needing human resolution. This is the primary output for senior engineer review.
- **`norm_extraction_prompt`** — asks the LLM to produce a structured JSON array of norms for machine processing in later pipeline stages.

Both prompts are written as `{system, user}` JSON (for any chat-completion API) and as `.md` (for copy/paste into a web UI). Deliberately LLM-agnostic — GPT-4o, Gemini, Claude, Llama, or any capable model will work.

**Sample output** from Gemini 2.5 Pro against `rust-lang/rust` is available in [`data/synthesised/LLMOutput/`](./data/synthesised/LLMOutput/) — showing 6 candidate standards, a correctly surfaced line-length conflict with contradicting quotes from the same reviewer on different PRs, and a clean separation of tooling concerns from principles.

### Phase 3 — Classify `[planned]`

Separate style signals from one-off engineering judgements. Tag each comment by category (architecture, naming, testing, error-handling, etc.) and type (principle / convention / tooling-rule / preference / exception).

### Phase 4 — Output `[planned]`

Produce two artefacts:
1. **Human decision register** — candidate rules with evidence counts, proponents, opponents, and explicit contradictions for human resolution
2. **`agents.md`** — compact operational policy for coding agents

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your GitHub token
export GITHUB_TOKEN=ghp_...      # Linux/macOS
$env:GITHUB_TOKEN = "ghp_..."    # PowerShell

# Run the harvester (defaults to rust-lang/rust, 2014-06-01..2014-08-31)
python -m harvester

# Build the synthesis prompts
python -m synthesiser

# Send the decision register prompt to your preferred LLM
# e.g. paste data/synthesised/register_prompt.md into any web UI,
# or POST data/synthesised/register_prompt.json to any chat-completion API
```

Outputs:
```
data/raw/
  prs.jsonl                        PR metadata
  issue_comments.jsonl             General thread comments
  review_comments.jsonl            Inline diff comments

data/synthesised/
  register_prompt.json             {system, user} -> human decision register
  register_prompt.md               Human-readable version for copy/paste
  norm_extraction_prompt.json      {system, user} -> JSON norms array
  norm_extraction_prompt.md        Human-readable version
```

The `register_prompt` is the primary output at this stage. Run it against any capable LLM to produce a human-reviewable decision register — see [`data/synthesised/LLMOutput/`](./data/synthesised/LLMOutput/) for an example.

### Configuring the target repository

Edit [`harvester/config.py`](./harvester/config.py):

```python
REPO      = "your-org/your-repo"
DATE_FROM = "2022-01-01"
DATE_TO   = "2024-12-31"
```

The harvester handles the GitHub Search API's 1,000-result cap automatically by splitting large date ranges into monthly sub-queries.

---

## The Norm Schema

Each extracted standard is represented as a `Norm`. The schema was designed to answer five questions for every candidate rule:

| Question | Field |
|---|---|
| What is the rule? | `statement` |
| Why does it exist? | `rationale` |
| Where does it apply? | `scope`, `applicability` |
| How is it enforced? | `enforcement_mode` |
| Should old code be changed? | `migration_policy` |

Key fields:

| Field | Values |
|---|---|
| `category` | architecture / naming / testing / error-handling / security / formatting / documentation / api-design |
| `type` | principle / convention / tooling-rule / preference / exception |
| `scope` | business / domain / repository / module / individual |
| `strength` | strong-consensus / moderate / weak-signal / contested |
| `enforcement_mode` | linter / formatter / build-ci / code-review / agent-guidance / documentation-only |
| `migration_policy` | no-retrofit / opportunistic / touched-code-only / new-projects-only / mandatory |
| `status` | proposed / accepted / rejected / superseded / deprecated |

The `type` field is the most important guard against producing bad policy. A `preference` (one reviewer's habit) is very different from a `principle` (an engineering outcome that matters). The synthesis prompt asks the LLM to make this distinction explicitly.

---

## Design Principles

**Scope matters.** A business-wide principle is different from a repo-local convention or an individual reviewer's preference. The schema tracks this explicitly and the synthesis prompt is designed to surface it.

**Migration policy is not optional.** Every norm must state whether old code should be retrofitted. This project defaults to `no-retrofit` for acquired or legacy codebases — the goal is to guide new work, not generate churn.

**Two outputs, not one.** The human decision register is what gives the agent policy its legitimacy. The `agents.md` is the distilled end product, not the starting point.

**Tooling over debate.** Formatting, import ordering, and naming casing belong in linters and formatters, not in agent guidance. The synthesis prompt explicitly separates these.

**Historical drift is not inconsistency.** If a reviewer's position changed over time, that may represent evolution, not contradiction. The norm schema records timelines for this reason.

---

## Repository Structure

```
harvester/                        Phase 1 — GitHub API data collection
synthesiser/                      Phase 2 — LLM prompt construction
planning/                         Source planning documents (see MAKING_OF.md)
data/raw/                         Harvested JSONL output (gitignored)
data/synthesised/                 Generated prompts (gitignored)
data/synthesised/LLMOutput/       Sample LLM output committed as demo
```

---

## Planned Deliverables

1. **Review corpus store** — normalised JSONL of PRs, comments, reviews, authors, timestamps
2. **Extracted norm register** — candidate rules with evidence counts, proponents, opponents, confidence
3. **Conflict report** — explicit contradictory guidance for human resolution
4. **Draft engineering standards** — human-readable decision document
5. **`agents.md`** — compact operational policy for coding agents, structured around precedence:
   1. Repository-local config and docs
   2. Formatter, linter, CI requirements
   3. Business-wide engineering principles
   4. Avoid enforcing reviewer preferences as rules
   5. When contested, minimise churn and escalate

---

## Status

| Phase | Status |
|---|---|
| Harvest (GitHub REST API) | Complete |
| Synthesis prompt generation | Complete |
| LLM-generated decision register | **Viable end-to-end** — see sample output |
| Comment classification | Planned |
| Norm clustering & scoring | Planned |
| Conflict detection | Planned |
| Automated `agents.md` generation | Planned |

**The pipeline is runnable end-to-end today** from `python -m harvester` through to a human-reviewable decision register. Phases 3 and 4 automate what currently requires a human to review the LLM output and ratify candidates — which is intentional: the human ratification step is what gives the resulting `agents.md` its legitimacy.

The pipeline was validated against `rust-lang/rust` (June–August 2014), producing 2,139 review comments sampled down to 500 high-authority comments (~29K tokens) for the synthesis prompt. Sample output is in [`data/synthesised/LLMOutput/`](./data/synthesised/LLMOutput/).

---

## Data Sources

- **GitHub REST API** — issue comments, pull request reviews, pull request review comments (separate endpoints)
- **GHArchive on Google BigQuery** — bulk historical extraction without API rate limits; query `githubarchive.year.*` or `githubarchive.month.*`, always filter by `repo.name`
- **GraphQL API** — review threads and resolution state (planned)
