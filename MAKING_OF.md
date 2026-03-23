# The Making Of

## How this project went from two chat conversations to a working prototype — without a human writing a line of code

---

## The Starting Point

This project began with two conversations — one with ChatGPT, one with Gemini — exploring a practical idea: rather than writing a greenfield coding standards document, could a company use its own GitHub PR history to excavate the standards its reviewers had already been enforcing?

Both conversations are preserved verbatim in [`planning/`](./planning/). Read them if you want the full intellectual backstory. The short version:

- **[chatgpt.md](./planning/chatgpt.md)** — A deep architecture and schema conversation covering GitHub's fragmented PR data model, the four-phase pipeline concept, a detailed `Norm` and `EvidenceItem` schema, the distinction between principles / conventions / tooling-rules / preferences, and why two output artefacts (human register + compact `agents.md`) matter
- **[gemini.md](./planning/gemini.md)** — A more practical conversation about test repositories, why `rust-lang/rust` is an ideal trial corpus, GHArchive and BigQuery as an alternative to the rate-limited REST API, and a suggested BigQuery SQL query for targeted extraction

Those two documents together formed a remarkably complete brief. The architecture was sound, the schema was thought through, the data sources were identified, and the risks were named. What was missing was any actual code.

---

## Handing It to an Agent

The planning documents were committed to an empty repository. A `CLAUDE.md` project brief was written distilling the key decisions — the pipeline phases, the schema definitions, the design principles — and that brief was loaded into a Claude Code session.

The instruction to the agent was simple: build it.

What followed is the entire git history of this repository. There was no separate design phase, no tickets, no sprint planning. The agent read the planning documents, understood the architecture, and started writing.

---

## What the Agent Built

### Phase 1 — The Harvester

The first thing built was the complete data collection pipeline in `harvester/`:

- `config.py` — configuration with sensible defaults (targeting `rust-lang/rust` for the trial)
- `models.py` — typed dataclasses for `PRRecord`, `IssueCommentRecord`, `ReviewCommentRecord`
- `client.py` — a GitHub REST API client with rate-limit handling and pagination
- `search.py` — PR search with automatic monthly splitting when results exceed GitHub's 1,000-item Search API cap
- `fetch.py` — per-PR fetchers for issue comments and review comments
- `store.py` — append-mode JSONL writer with `.progress` tracking for resumable runs
- `__main__.py` — the orchestrating entry point

The agent also set up the git repository, created the GitHub remote as a private repo, and made the initial commit — including fixing a corrupted `.git` directory that existed from a prior aborted initialisation.

### The Trial Run and the First Bug

The harvester was run against `rust-lang/rust` immediately. It began downloading, then crashed:

```
TypeError: 'NoneType' object is not subscriptable
  File "harvester/fetch.py", line 42, in fetch_review_comments
    author=comment["user"]["login"],
```

The bug: GitHub returns `null` for the `user` field on comments from deleted accounts. A 2014 corpus has a non-trivial number of these.

The fix was a one-liner applied to both fetch functions:

```python
# Before
author=comment["user"]["login"],

# After
author=(comment["user"] or {}).get("login", "[deleted]"),
```

The run resumed automatically from the `.progress` checkpoint — which is exactly what the resumable design was there for.

### Phase 2 — The Synthesis Prompt

Once the harvester was working, the synthesiser was built. An initial version called the Claude API directly. This was immediately revised on reflection: locking the pipeline to a single LLM vendor was unnecessary. The synthesiser's job is to prepare the input, not to decide who processes it.

The revised version simply builds a structured prompt and writes it to disk:

- `data/synthesised/prompt.json` — `{"system": "...", "user": "..."}` for any chat-completion API
- `data/synthesised/prompt.md` — human-readable for copy/paste

The system prompt asks the model to identify recurring reviewer patterns, distinguish principles from preferences, and output a JSON array of norm objects with fields matching the schema designed in the planning conversations. The user message contains all harvested review comments, stripped of diff hunks (which roughly halves the token count without losing the normative content).

---

## What the Trial Data Showed

The rust-lang/rust corpus from June–August 2014 produced:
- 671 merged PRs in the date range
- ~651 review comments by the time the run was interrupted and resumed
- ~182 issue thread comments

Even a quick look at the review comment bodies confirmed the approach has legs. Reviewers like `alexcrichton` were consistently enforcing documentation structure, error handling conventions, and API design patterns across multiple PRs and files. These are exactly the kind of recurring signals the synthesis prompt is designed to surface.

---

## Reflections on the Process

### What worked well

**The planning documents paid off immediately.** Because the architecture had been properly thought through before any code was written, the agent had a genuine brief to work from rather than having to guess intent. The schema was defined, the phases were named, the design principles were explicit. The agent didn't need to make structural decisions — it needed to implement decisions that had already been made.

**The two-stage approach (plan then code) produced clean code.** The harvester is modular, resumable, and handles edge cases (rate limits, deleted users, API result caps) that a rushed implementation might have missed. These weren't afterthoughts; they came from the planning conversations.

**Bugs were handled as bugs.** When the deleted-user crash happened, the agent diagnosed it correctly, applied a minimal fix, and resumed. There was no attempt to restructure the fetcher or add unnecessary defensive code — just the one guard that was actually needed.

**The agent stayed close to the brief.** At no point did the implementation drift into scope creep. The synthesiser was initially written with a direct Claude API call, but when reconsidered it was rebuilt as prompt-only without complaint. The principle — avoid locking to a vendor where there's no reason to — was correctly applied.

### What this demonstrates

This project is a proof of concept for a specific kind of AI-assisted development: **planning with AI, then implementing with AI**.

The two planning conversations are not prompts to a coding agent. They're a design process — exploratory, iterative, occasionally speculative. The value is that they forced the project to think through schema design, failure modes, output formats, and organisational risks before any code existed. That thinking is documented, auditable, and still visible in `planning/`.

The coding agent then took that design and built it. The human's job in the implementation phase was to run the code, observe what happened, and give feedback. The loop was:

```
run → observe → feedback → run
```

Not:

```
write → review → write → review
```

This is a meaningful shift. It doesn't eliminate human judgement — the trial run, the decision to make the synthesiser LLM-agnostic, the choice of which repo to test against — all of those required human decisions. But the mechanical work of translating a design into working code was handled by the agent.

### The limits worth noting

**The planning documents were unusually good.** Not every design conversation will produce a brief this complete. The ChatGPT conversation in particular went deep on schema design, failure modes, and the distinction between different types of norms. That depth translated directly into the quality of the synthesiser prompt. Weaker planning would have produced weaker code.

**This is a prototype, not a product.** Phases 3 and 4 (classification, clustering, conflict detection, output generation) are planned but not built. The value of the current state is that it proves the pipeline works end-to-end for Phase 1, and that the Phase 2 prompt is ready to send to any capable LLM.

**The real test is on a company codebase.** `rust-lang/rust` is an excellent trial corpus but it's an open-source compiler with a particular review culture. The meaningful validation is running the harvester against a real company's repositories and seeing whether the synthesis output is actually useful to senior engineers reviewing it.

---

## The Broader Point

There's a temptation to use AI coding assistants as fast typists — give them a small task, check the output, iterate. That works. But it undersells the capability.

The more interesting use is: **think through your problem with AI, then build it with AI**. The planning conversations in `planning/` are not documentation added after the fact. They are the actual intellectual work that made the implementation possible. The agent didn't invent the architecture — it implemented an architecture that had been properly developed.

The question this project is designed to answer — can you extract implicit coding standards from PR history? — turns out to apply to the project itself. The standards that produced this code are visible: in the schema design choices, in the decision not to lock to a single LLM, in the resumable harvester, in the separation of the human decision register from the agent policy document. Those standards came from the planning conversations. The code reflects them faithfully.

That's probably the most honest advertisement for what this tool can do.

---

## Reproducing This

If you want to run the same process against your own repositories:

1. Read the planning documents to understand the architecture
2. Clone this repo
3. Set `REPO`, `DATE_FROM`, `DATE_TO` in `harvester/config.py`
4. Run `python -m harvester` with a `GITHUB_TOKEN`
5. Run `python -m synthesiser`
6. Send `data/synthesised/prompt.json` to your preferred LLM
7. Review the extracted norms with your senior engineers
8. Resolve conflicts, accept or reject candidates, and freeze the result into `agents.md`

The human step — step 7 — is the one that cannot be automated. That's by design.
