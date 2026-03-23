
Can you explain to me a little bit about the scope for a coding agent, an AI agent, to read and ingest from a repository the threaded discussions in a pull request, assuming GitHub as the repository provider?

I’m checking the current GitHub surfaces an agent can use here, because the practical answer depends on whether you mean GitHub App/API access, Actions, or an external agent watching PRs.

There are really three distinct conversation streams on a GitHub PR, and an agent usually needs all three: general PR conversation, review summaries/approvals, and inline diff-thread comments. I’m pulling the precise API boundaries so I can explain what’s easy versus awkward.

Thought for 33s

Yes. In GitHub terms, an agent can absolutely ingest PR discussion, but it needs to understand that a pull request’s “conversation” is split across different objects and events rather than existing as one neat transcript. The main buckets are:

1.  **General PR comments** on the Conversation tab, which are exposed through the **issue comments** APIs because every PR is also an issue.
2.  **Reviews** such as “Approved”, “Changes requested”, plus any overall review body text, which are available through the **pull request reviews** APIs. GitHub documents these reviews as being returned in chronological order.
3.  **Inline diff comments and threads** attached to specific lines or hunks of the diff, which are handled separately as **pull request review comments** and review threads. GitHub distinguishes these from both issue comments and commit comments.

So the real scope is quite broad: a coding agent can build a fairly rich model of “what reviewers are saying, where in the code they said it, whether the author replied, and whether the concern appears resolved.” That is enough for some very useful behaviours.

A practical agent can do all of these:

-   read the PR metadata, changed files, and patch/diff;
-   fetch top-level PR conversation comments;
-   fetch reviews and their states such as approval or changes requested;
-   fetch inline review comments tied to files and diff positions;
-   observe thread state changes such as review-thread resolution via webhook events;
-   correlate comments back to exact files, lines, commits, and revisions.

That means an agent can answer things like:

-   “What concerns are still outstanding on this PR?”
-   “Which review comments were about naming vs logic vs tests?”
-   “Has the author addressed the performance concern raised on `FooService.cs`?”
-   “Summarise all unresolved reviewer asks into a checklist.”
-   “Generate follow-up commits aimed at the open review threads.”

Where people often overestimate things is in assuming GitHub hands you one canonical threaded discussion object for the whole PR. It doesn’t, at least not in the simple REST sense. You usually have to combine multiple sources:

-   issue comments for general discussion,
-   review objects for review-level intent/state,
-   review comments or GraphQL review threads for inline discussion,
-   timeline/webhooks for event flow and state changes.

In practice, the best implementation pattern is usually one of these.

**External agent or service**  
A GitHub App or service account listens to PR-related webhooks, then calls the GitHub APIs to hydrate the full context. GitHub exposes distinct webhook/event surfaces for `issue_comment`, `pull_request_review`, `pull_request_review_comment`, and `pull_request_review_thread`. That makes event-driven ingestion quite workable.

**GitHub Actions-based agent**  
A workflow can run on PR, review, or comment events. GitHub explicitly separates workflow triggers for `pull_request_review`, `pull_request_review_comment`, and `issue_comment`, rather than treating them as one PR-comment stream.

**Clone-and-analyse coding agent**  
A more code-focused agent can clone the repository, inspect the checked-out branch, then call GitHub APIs for the PR discussion layer. This is often the sweet spot for coding agents because repository ingestion alone does not include the review discussion; that has to come from the platform API.

The main technical limitations are:

**1. Discussion is fragmented.**  
An agent must merge multiple feeds into one internal conversation graph. Otherwise it will miss things like a top-level reviewer complaint that never appears inline, or an inline thread that never appears in a simple comments list.

**2. Diff-relative comments are tricky.**  
Inline comments are attached to diff positions/hunks, not just abstract file names. GitHub’s review comment docs describe positions relative to the `@@` hunk headers in the diff, which means an agent needs to understand patch context rather than only the final file contents.

**3. “Resolved” does not necessarily mean “fixed.”**  
A resolved review thread may simply have been manually marked resolved. An agent still has to compare thread content against subsequent commits and code state before declaring the concern genuinely addressed. The webhook surface can tell you that a thread was resolved, but not whether the underlying engineering issue was actually fixed to your standards.

**4. Permissions matter.**  
GitHub documents different permission requirements for different surfaces. For example, listing reviews requires read access to Pull Requests permissions for fine-grained tokens, and subscribing to some webhook events depends on app permissions such as Issues, Pull requests, or Contents depending on the event.

**5. Fork and trust boundaries matter.**  
If you run the agent inside Actions on untrusted PRs from forks, you need to be careful. GitHub notes that first-time contributors to public repos may require maintainer approval before workflows run. That matters a lot if the agent is intended to read secrets or post privileged replies.

Conceptually, I’d think of the agent’s ingestion model like this:

-   **Repository state**: base branch, head branch, changed files, patch, tests, code ownership.
-   **Human discussion state**: issue comments, reviews, inline threads, reactions, resolution state.
-   **Derived task state**: open concerns, likely fixes, uncertain items, blocked-by-human items.

Once you model it that way, the agent can do more than summarise. It can:

-   cluster comments into themes;
-   map comments to code symbols or files;
-   detect stale comments after rebases or force-pushes;
-   propose commits targeted at unresolved threads;
-   draft author replies with evidence from the latest diff;
-   keep a rolling “review debt” summary per PR.

The most realistic near-term use is not “autonomously participate like a perfect reviewer,” but “maintain a high-quality machine-readable map of reviewer intent.” That alone is very powerful. It lets the agent turn an untidy PR discussion into:

-   unresolved asks,
-   accepted suggestions,
-   disputed points,
-   comments needing human judgement,
-   comments invalidated by later commits.

So the answer is: **the scope is substantial**, and GitHub gives enough API/webhook surface for it, but a serious agent needs to ingest both the repo and the PR discussion model, not just scrape comments. The hard part is not access; it is stitching the various comment/review/thread/event types into a coherent state machine.

I can sketch a concrete architecture for this next, either as a GitHub App design or as a simpler “polling script + LLM” approach in .NET or Node.

Great. Well, we're thinking of this as a way to collate past comments from across multiple existing repositories to try to piece together a house style which could then be fed to agents as the company's preferred approach to coding. I think it would be largely a one-off exercise. So we would want to synthesise all of the history of discussions, changes, comments, criticisms, resolutions, and surface any inconsistencies. Have we got a senior dev saying different things on different days or two different senior devs saying different things where a decision needs to be made? And at the end of the process, we would come out with effectively an agents.md after the collating and discussing and resolving of inconsistencies that could be used as the basis for new code going forward.

This is a much more interesting use case than “reply to this PR.” I’m checking the current GitHub capabilities around historical extraction and searchability, because the main constraint here is usually bulk collection and normalisation rather than the LLM step itself.

Thought for 22s

Yes — that is a very plausible one-off mining exercise, and in some ways it is a **better fit for AI than live PR participation**.

The reason is that you are not asking the agent to make instant merge decisions. You are asking it to do what LLMs are relatively good at: ingest a large body of semi-structured human discussion, cluster repeated themes, detect contradictions, and turn them into a draft policy document. GitHub gives you enough API surface to collect the raw material, because PR history can be harvested from general PR comments, review summaries/states, and inline review comments on diffs. Those are exposed separately through the Issues, Pull Request Reviews, and Pull Request Review Comments APIs, rather than as one unified transcript.

The important thing is to think of the job in **four phases**, not one.

## 1. Harvest everything into a normalised review corpus

For each repository, you would want to collect at least:

-   PR metadata: title, description, author, dates, reviewers, labels, merge outcome
-   top-level conversation comments
-   reviews and review states such as approved / changes requested
-   inline diff comments
-   ideally the changed files and patch context for the commented code

GitHub’s docs make clear that top-level PR comments live under the issue-comment model because every PR is also an issue, while diff comments are separate review comments, and review objects are a further separate entity returned chronologically.

That means your first engineering task is not “ask the AI what our style is.” It is:

**build a unified internal schema** such as:

-   Repository
-   PullRequest
-   ReviewEvent
-   Comment
-   ReviewThread
-   File
-   LineRange
-   CommitSnapshot
-   ResolutionSignal

Once you have that, you can flatten ten thousand fragmented GitHub remarks into a single queryable corpus.

## 2. Separate style signals from one-off engineering judgements

A major trap is that many PR comments are **not** about house style at all. They may be about:

-   a specific bug in a specific feature
-   a business rule misunderstanding
-   a missing migration
-   a one-off performance concern
-   a temporary team preference later abandoned

So the agent needs a classification pass before synthesis. A useful taxonomy would be:

-   naming and terminology
-   architecture and layering
-   testing expectations
-   error handling / logging
-   API design
-   nullability / type safety
-   front-end patterns
-   state management
-   performance / scalability
-   security / secrets / auth
-   documentation / readability
-   team process rather than code style

This is where the project becomes valuable: you are not only extracting “what people said”, you are estimating **which remarks are actually normative**.

A reviewer saying “please rename this variable” once is weak evidence.  
A reviewer saying variants of “service layer must not leak DTOs” across 27 PRs in 3 repositories is strong evidence.

## 3. Detect consistency, inconsistency, and authority

This is the heart of your idea.

You want the agent to be able to say things like:

-   “Senior Dev A repeatedly prefers explicit mapping over AutoMapper in service boundaries.”
-   “Senior Dev B objects to repository abstractions in older PRs but endorses them in later PRs.”
-   “Different reviewers disagree on whether controller actions should return domain errors or map to problem details centrally.”
-   “There is stable consensus on unit testing of business-rule code, but inconsistent advice on integration tests.”
-   “Frontend repositories use conflicting guidance on hooks vs helper modules.”

That is absolutely feasible, but only if the agent records **who said what, when, where, and with what outcome**.

So for each candidate “rule”, the extracted evidence should include:

-   quoted or paraphrased statement
-   speaker
-   repo and PR
-   date
-   whether others agreed, disagreed, or ignored it
-   whether the subsequent code change implemented that advice
-   whether later comments reinforced or contradicted it

This matters because not all comments should be weighted equally. In practice you would probably apply scoring such as:

-   frequency across repos
-   recency
-   seniority/role of reviewer
-   whether the point was adopted in code
-   whether it recurs independently from multiple reviewers
-   whether it survived over time

That helps you distinguish:

-   **house rules**
-   **personal preferences**
-   **historical artefacts**
-   **active disagreements needing decision**

## 4. Produce two outputs, not one

You mentioned ending with effectively an `agents.md`. I would actually produce **two artefacts**:

### A. Decision-prep document for humans

This is the “working paper” for your senior developers.

It should contain:

-   candidate standards with evidence
-   areas of strong consensus
-   areas of ambiguity
-   direct contradictions
-   questions needing explicit decision
-   examples from real PR history

For example:

> **Candidate rule:** Service layer should not return persistence models  
> **Evidence:** 14 comments across 3 repos from A, C, and D  
> **Confidence:** High  
> **Conflicts:** none found  
> **Suggested wording:** “Map persistence entities before crossing service boundaries.”

Or:

> **Candidate rule:** Prefer AutoMapper for internal mappings  
> **Evidence:** mixed  
> **Conflict:** A generally opposes hidden mappings; B endorsed AutoMapper in 2024 migration PRs  
> **Needs decision:** yes

### B. Machine-usable `agents.md`

This should be much shorter and more normative.

Structure it as:

-   coding principles
-   repo-specific exceptions
-   examples of preferred / non-preferred patterns
-   review priorities
-   “when to ask a human”
-   conflict escalation rules

That second artefact is what you feed to agents.

The first artefact is what gives the second one legitimacy.

## What the pipeline would look like

At a high level:

1.  Enumerate repositories
2.  Enumerate PRs, probably closed and merged first
3.  Pull comments, reviews, review comments, changed files, timestamps
4.  Store in a normalised database
5.  Run LLM-assisted extraction of candidate “norm statements”
6.  Cluster semantically similar statements
7.  Score for confidence and consistency
8.  Identify contradictions
9.  Draft a standards document
10.  Put that draft in front of senior humans for adjudication
11.  Freeze the result into `agents.md` plus optional repo supplements

That is the right order.  
You do **not** want to point an LLM straight at raw PR history and ask, “what is our coding style?” You will get mush.

## Where GitHub itself helps and where it does not

GitHub helps with retrieval, but not much with synthesis.

It supports filtering/searching issues and PRs, including review-status filters in the UI/CLI, which is useful for scoping what you collect. But GitHub’s search/filtering is not the same thing as a historical style-analysis engine; you still need your own extraction layer.

For a one-off retrospective exercise, I would not bother with webhook/event-driven infrastructure unless you later want continuous updates. GitHub does have webhook surfaces for `pull_request_review`, `pull_request_review_comment`, and `pull_request_review_thread`, but that is more useful for an ongoing monitor than for a one-time historical mining project.

## The biggest risks

There are a few, and they are more organisational than technical.

### 1. Mistaking reviewer noise for policy

Some people comment heavily but inconsistently.  
The system must not turn “Nigel had a bad Wednesday” into doctrine.

### 2. Context collapse

A comment like “please avoid this” may refer to:

-   this exact pattern in this exact file
-   this technique in general
-   this approach only because of a release constraint

The agent needs surrounding context from the diff and perhaps the file type/module.

### 3. Historical drift

Your standards may genuinely have changed over time.  
That is not inconsistency; it may be evolution.

So the agent should detect timeline shifts:

-   “Before 2025 the team tolerated fat controllers; after 2025 reviewers consistently pushed orchestration into services.”

### 4. Authority ambiguity

A company does not necessarily want its style guide inferred democratically from all comments.  
You may want comments from designated maintainers or lead reviewers to count more heavily.

### 5. Survivorship bias

Merged code is not proof that reviewers were happy. Sometimes people just gave up.  
So adoption in the code should be one signal, not the only signal.

## My honest view on viability

This is very viable **if you treat it as knowledge distillation with a human ratification step**.

It is not viable if the goal is:  
“Let the AI infer our coding constitution automatically and declare the truth.”

The sweet spot is:

-   AI does the reading
-   AI proposes candidate norms
-   AI highlights conflicts
-   humans resolve the conflicts
-   the resolved document becomes the real standard

That gives you something robust enough to feed to coding agents.

## What I would recommend as the actual deliverables

I’d aim for this set:

1.  **Review corpus store**  
    JSON or database containing PRs, comments, reviews, files, timestamps, authors.
2.  **Extracted rule register**  
    A table like:
    -   rule candidate
    -   category
    -   evidence count
    -   first seen
    -   last seen
    -   main proponents
    -   main opponents
    -   confidence
    -   needs decision?
3.  **Conflict report**  
    Explicitly listing contradictory guidance.
4.  **Draft engineering standards**  
    Human-readable decision document.
5.  **Final `agents.md`**  
    Compact, stable, operational.

## The encouraging bit

Your idea is actually stronger than a generic style guide exercise, because it is grounded in **what your reviewers have historically cared about in real code**. That means the resulting `agents.md` is much more likely to align with lived team norms than a greenfield standards document written from scratch.

And it should be excellent fuel for agents, because agents need exactly this sort of explicit, local policy:

-   what matters here
-   what to avoid here
-   what reviewers will object to here
-   what is preference versus hard rule
-   when the model should stop and ask

The result is less “AI invents our standards” and more “AI helps us excavate and formalise the standards we’ve been enforcing informally.”

I can turn this into a concrete implementation plan next — for example:  
a minimal one-off pipeline in Python/.NET,  
or a proposed schema for the extracted corpus and conflict report.

Yes, fully agree on the iterative nature of the task. I mentioned Agents.md as the ultimate output as the impetus is to enable coding agent adoption. Certainly there will be touchpoints along the way where human review and decision-making is required, including the decision that there is no need for a business-wide standard but that linting should ensure consistency within a project. Otherwise you get stupid situations where a corporate acquisition brings in an excellent, internally-consistent codebase but effort is needlessly expended on making in comply with essentially arbitrary local choices!

Thought for a few seconds

Exactly. That is a very sensible distinction, and it is one many teams fail to make.

What you are really trying to extract is not “one true corporate coding style”, but a hierarchy something like this:

-   **non-negotiable engineering principles**
-   **project-level conventions**
-   **tool-enforced formatting and lint rules**
-   **personal reviewer preferences that should not become policy**

That avoids the absurd outcome where consistency is pursued for its own sake, even when the incoming codebase is coherent, high-quality, and already optimised around its own architecture.

The acquisition example is a very good one. A mature codebase may be internally consistent in:

-   naming,
-   layering,
-   test style,
-   dependency patterns,
-   error handling,
-   component structure,

and yet differ from local house taste on superficial points. Forcing wholesale convergence can easily destroy value rather than create it. In practice, the cost is not just engineer time; it also introduces noise into blame history, obscures meaningful changes in PRs, and risks breaking stable patterns that made sense in that codebase.

So the mining exercise should ideally not ask only:

**“What standards do our senior devs seem to want?”**

It should also ask:

**“At what level are they expressing that preference?”**

That is, each extracted norm should be classified as one of these:

### 1. Universal principle

These are the ones most worth feeding to agents across the business.

Examples:

-   keep business logic out of controllers
-   make error handling explicit
-   avoid hidden side effects
-   write tests around business rules
-   protect secrets and auth boundaries carefully
-   prefer clear, maintainable code over cleverness

These are portable because they are tied to engineering outcomes, not taste.

### 2. Stack-specific or architecture-specific convention

These may be valid only for certain repos.

Examples:

-   in React projects, use hooks in a particular way
-   in .NET APIs, map DTOs at a certain layer
-   in this event-driven service, use a specific message schema pattern
-   in this repo, use MediatR; in that repo, do not

These belong either in per-project supplements or in tagged sections of the guidance.

### 3. Tooling convention

These are best enforced mechanically, not debated endlessly.

Examples:

-   brace placement
-   import ordering
-   naming casing
-   file layout
-   quote style
-   linting thresholds
-   nullable warnings as errors

Agents should know these, but the real source of truth should be the formatter, linter, and CI pipeline.

### 4. Reviewer preference

This is the dangerous category.

Examples:

-   “I prefer extension methods here”
-   “I would have named this differently”
-   “I don’t like this pattern”
-   “I usually split methods sooner”

These are not worthless, but they should not automatically become institutional doctrine. They should be recorded as weak evidence unless they recur broadly and survive challenge.

That gives you a much healthier end product. Instead of a monolithic `agents.md`, you might end up with something like:

-   `engineering-principles.md`
-   `project-conventions/<repo>.md`
-   `linting-policy.md`
-   `agents.md` as the operational distillation for coding agents

Where `agents.md` says, in effect:

-   obey formatter/linter first;
-   follow repo-local conventions before business-wide preferences;
-   apply business-wide engineering principles across all work;
-   where historical reviewer guidance conflicts, prefer the explicit repo standard or escalate.

That is a far better instruction set for an agent than “use PascalCase here because that’s what Dave liked in 2023.”

The other important thing you touched on is that the exercise may conclude that **uniformity is not the goal**. That is not failure; that is a useful discovery.

A mature outcome could be:

-   we want **shared principles** across the business;
-   we want **consistency within each repo**;
-   we do **not** want to normalise every repo into one aesthetic;
-   we do want clear rules for new projects;
-   we want migration only where inconsistency causes real maintenance cost.

That is a very defensible policy, and frankly more modern than old-style “everything must look the same” governance.

From an agent-adoption point of view, that actually works well, because agents do not require one giant universal rulebook. They need a clear precedence order. For example:

1.  repository-local docs and config
2.  formatter/linter/build rules
3.  shared engineering principles
4.  explicit human instructions in the ticket/PR
5.  otherwise ask or choose the least disruptive option

That ordering prevents the agent from trying to “improve” a repo into some abstract corporate ideal.

So I would design the mining and synthesis stages to produce not just candidate rules, but also metadata like:

-   **scope**: business-wide / domain / repo / team / individual
-   **type**: principle / convention / tooling / preference
-   **strength**: strong consensus / mixed / contested
-   **enforcement mode**: human review / linter / CI / agent guidance
-   **migration advice**: apply only to new code / apply opportunistically / no retrofit needed / consider codemod

That last field is especially important for avoiding the pointless churn you’re describing. Some rules should clearly say:

-   applies to **new projects only**
-   applies to **touched code only**
-   applies **only when refactoring anyway**
-   do **not** rewrite stable legacy code solely to comply

That one distinction could save a huge amount of wasted effort.

So yes, I think your framing is exactly right:  
the exercise is not really about discovering “the standard”;  
it is about discovering **which things deserve to be standardised, at what level, and with what enforcement mechanism**.

That is the kind of nuance that would make the eventual agent guidance genuinely useful rather than oppressive.

The next concrete step I’d suggest is to define the target output schema for each extracted norm before any large-scale mining begins. That forces the project to distinguish principle from preference right from the start.

Yes. I'm open to suggestions here, keeping it programming language-agnostic, please

I’m going to ground this in the current GitHub surface, then I’ll propose a language-agnostic schema and workflow you can use regardless of whether the pipeline ends up in Python, .NET, or something else.

Thought for 13s

Yes — I’d define the output schema **before** you mine anything, and I’d keep it deliberately neutral about language, framework, and even repository topology.

What you want is not a schema for code.  
It is a schema for **norms inferred from review history**.

A good model is to treat each extracted item as a **candidate engineering norm** with evidence, scope, and status.

## Recommended core schema

I’d use something like this as the canonical unit:

Norm  
- id  
- title  
- statement  
- rationale  
- category  
- scope  
- applicability  
- enforcement_mode  
- strength  
- status  
- migration_policy  
- evidence_summary  
- supporting_examples[]  
- conflicting_examples[]  
- related_norm_ids[]  
- human_owner  
- last_reviewed_at

And then define each field carefully.

## Field definitions

### `title`

A short label.

Examples:

-   Keep business logic out of transport handlers
-   Prefer explicit error handling at boundaries
-   Enforce formatting mechanically
-   Avoid cross-layer leakage of persistence models

### `statement`

A plain-English norm, written as something an engineer or agent can follow.

Examples:

-   “Business rules should live in domain or service code, not in route handlers, controllers, or UI actions.”
-   “Formatting and import ordering should be delegated to automated tooling, not debated in code review.”

This should be imperative and concrete.

### `rationale`

Why the rule exists.

This is important because agents and humans both benefit from understanding intent.  
A rule with rationale is easier to apply sensibly and easier to exempt when needed.

Example:

-   “This reduces hidden coupling, improves testability, and keeps boundary code thin.”

### `category`

A controlled vocabulary. I would keep this small.

Suggested values:

-   architecture
-   boundaries
-   naming
-   testing
-   error-handling
-   security
-   performance
-   readability
-   documentation
-   dependency-management
-   state-management
-   formatting
-   process

These are for clustering and reporting, not for end-user prose.

### `scope`

This is one of the most important fields.

Suggested values:

-   business
-   domain
-   platform
-   repository
-   module
-   team
-   individual

This lets you distinguish:

-   business-wide principles,
-   repo-local conventions,
-   and “just something one reviewer tends to say.”

### `applicability`

This answers “when does this apply?”

Suggested structure:

-   all code
-   new projects only
-   new code only
-   touched code only
-   specific repository types
-   specific architectural style
-   specific risk areas only

This stops every norm turning into a mandatory retrofit exercise.

### `enforcement_mode`

Suggested values:

-   linter
-   formatter
-   build/ci
-   code-review
-   architecture-review
-   agent-guidance
-   documentation-only

This is crucial because many style questions should not live in human discussion at all. GitHub gives you access to PR comments, reviews, and review comments, but your synthesis should often conclude that some norms belong in tools rather than future review debate. GitHub’s APIs separate top-level issue comments, reviews, and diff comments, which makes it practical to mine those different forms of review evidence into one corpus.

### `strength`

This is your confidence / consensus measure.

Suggested values:

-   strong-consensus
-   moderate-consensus
-   weak-signal
-   contested
-   obsolete

You could generate this from evidence counts plus human ratification.

### `status`

Suggested values:

-   proposed
-   under-review
-   accepted
-   rejected
-   superseded
-   deprecated

This matters because your first output will not be final truth. It will be a working set.

### `migration_policy`

Suggested values:

-   no-retrofit
-   opportunistic
-   touched-code-only
-   new-projects-only
-   codemod-when-worthwhile
-   mandatory-retrofit

This is where you explicitly avoid the acquisition nightmare you mentioned.

### `evidence_summary`

A short prose summary of why the norm exists.

Example:

-   “Raised repeatedly across 4 repositories by 3 senior reviewers, usually in relation to maintainability and testability.”

### `supporting_examples[]`

A list of evidence items.

Each one should capture:

-   repo
-   PR number
-   date
-   speaker
-   comment type
-   short excerpt or paraphrase
-   outcome
-   confidence

GitHub exposes the underlying streams you need for this: PR conversation comments through issue comments, review summaries through pull-request reviews, and inline code discussion through review comments; review lists are returned chronologically, which is useful for reconstructing evolution over time.

### `conflicting_examples[]`

Same structure, but for contradictory or tension-producing evidence.

This is what lets you say:

-   “A preferred explicit mapping style is strong in Repo A but contradicted in Repo B.”
-   “Reviewer X changed position over time.”
-   “There is no business-wide consensus here.”

### `related_norm_ids[]`

Useful for linking things like:

-   thin boundary handlers
-   explicit mapping
-   test business rules
-   avoid hidden side effects

Those often travel together.

### `human_owner`

Who is responsible for final adjudication if the norm is disputed.

Not necessarily an individual forever; could be:

-   architecture group
-   platform lead
-   repo maintainers

### `last_reviewed_at`

Because norms age.

## A companion schema for raw evidence

I would also define a separate evidence record, because that is what the extraction pipeline will create first.

EvidenceItem  
- id  
- repository  
- pull_request_number  
- pull_request_url  
- merged_at  
- author  
- reviewer  
- comment_type  
- thread_type  
- file_path  
- line_reference  
- commit_sha  
- timestamp  
- body_excerpt  
- paraphrase  
- inferred_norm_candidate  
- sentiment  
- disposition  
- authority_weight  
- recency_weight

### `comment_type`

Suggested values:

-   top-level-pr-comment
-   review-summary
-   inline-review-comment
-   reply-in-thread

That reflects GitHub’s split model of PR discussion rather than pretending it is one homogeneous conversation.

### `disposition`

Suggested values:

-   accepted
-   rejected
-   discussed
-   unresolved
-   unclear

### `authority_weight`

Do not make this too clever initially.  
Maybe just:

-   reviewer role known maintainer / senior / general contributor / unknown

### `recency_weight`

Useful for detecting evolution:

-   old
-   mid
-   recent

## A classification model for each norm

I’d explicitly add one more dimension so that the final output stays sane:

NormType  
- principle  
- convention  
- tooling-rule  
- preference  
- exception

This is the field that keeps you from institutionalising arbitrary taste.

Examples:

**Principle**

-   Keep business logic away from transport/UI boundaries

**Convention**

-   Use a certain repository layout in service repos

**Tooling-rule**

-   Import ordering, formatting, line length

**Preference**

-   Reviewer tends to prefer extension methods here

**Exception**

-   In this repo, a specific pattern is accepted because of legacy framework constraints

## What the final outputs should look like

From that schema, you can generate three very useful deliverables.

### 1. Decision register

For humans.

Columns:

-   norm title
-   type
-   scope
-   strength
-   status
-   evidence count
-   conflicting evidence count
-   recommended action

### 2. Repo policy pack

Per repo or per repo family.

Contains:

-   accepted local conventions
-   exceptions to business-wide guidance
-   tooling expectations

### 3. `agents.md`

This should be a distilled operational version, not the evidence archive.

I would structure it around precedence:

1.  obey repository-local config and docs
2.  obey formatter, linter, and CI requirements
3.  follow accepted business-wide engineering principles
4.  avoid enforcing mere reviewer preferences as if they were rules
5.  when evidence is contested, minimise churn and escalate

That is much more useful to an agent than a giant document of mined quotations.

## A good minimal taxonomy

If you want a compact starting point, I’d begin with just these dimensions:

-   `type`: principle / convention / tooling-rule / preference / exception
-   `scope`: business / repository / module / individual
-   `strength`: strong / moderate / weak / contested
-   `status`: proposed / accepted / rejected / superseded
-   `migration_policy`: no-retrofit / touched-code-only / opportunistic / mandatory

That is already enough to prevent most nonsense.

## My recommended design principle

Every extracted norm should be able to answer five questions:

-   What is the rule?
-   Why does it exist?
-   Where does it apply?
-   How is it enforced?
-   Should old code be changed to match it?

If a candidate norm cannot answer those cleanly, it is probably not ready to become policy.

## One practical suggestion

I would also keep a field called `anti_goal` or `do_not_infer`.

Example:

-   “Do not treat formatting discussions as architectural policy.”
-   “Do not generalise comments tied to temporary migration constraints.”
-   “Do not turn one maintainer’s naming taste into a business rule without corroboration.”

That sounds slightly bureaucratic, but it is exactly the kind of guardrail that keeps the exercise honest.

So my suggestion, language-agnostically, is:

-   define a **Norm** schema,
-   define an **EvidenceItem** schema,
-   classify each norm by **type**, **scope**, **strength**, and **migration policy**,
-   and generate both a human decision register and a much shorter agent-facing policy file.

If you want, I’ll draft this next as a concrete JSON or YAML schema that you could hand to a coding agent as the target structure for extraction.