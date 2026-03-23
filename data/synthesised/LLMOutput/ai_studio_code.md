---
# Coding Standards Decision Register
## rust-lang/rust — June 2014 to July 2014

*Generated from 500 review comments. Requires human review and ratification.*

---
## Summary
This register was generated from a sample of 500 inline pull request comments and general thread discussions. The corpus provides a high-quality signal for documentation conventions, naming, and API design. We identified **6 candidate standards**, **1 major conflict** regarding line length limits, and several formatting rules that are prime candidates for automated tooling. Overall, the core team demonstrates strong consensus on API conventions (e.g., error handling and imports) but occasionally diverges on whitespace and formatting limits.

---
## Candidate Standards

### 1. Standardize Documentation Section Headers
**Rule:** Use top-level Markdown headers (`#`) for standard documentation sections like "Failure" and "Example".
**Category:** Documentation | **Type:** convention | **Strength:** strong-consensus
**Recommended action:** Accept as standard

**Evidence** (~2 comments):
> "Our current documentation style is to put the failure/example sections under their own header, like: `# Failure` ... `# Example`" — @alexcrichton, PR#14641
> "Could you add the `#` character in front of these sections?" — @alexcrichton, PR#14641

**Rationale:** Standardizing headers ensures consistent rendering in `rustdoc` and provides a uniform reading experience across the standard library.

### 2. Prefer Module-Level Imports in Documentation Examples
**Rule:** Avoid absolute or deeply nested paths (`std::os::setenv`) in documentation examples. Instead, import the module (`use std::os;`) and use a single layer of resolution (`os::setenv`).
**Category:** Documentation | **Type:** convention | **Strength:** strong-consensus
**Recommended action:** Accept as standard

**Evidence** (~3 comments):
> "Additionally, it's stylistically more acceptable to invoke functions through one layer of modules, `os::setenv` rather than two, `std::os::setenv`. Could you import `std::os` at the top?" — @alexcrichton, PR#14713
> "These two can be written as just `os::...` with a `use std::os;` added at the top." — @huonw, PR#14713

**Rationale:** This convention mirrors idiomatic Rust usage in actual code, keeping examples clean, concise, and pedagogical.

### 3. Lowercase Error Messages
**Rule:** Begin compiler and system error messages with a lowercase letter.
**Category:** Error Handling | **Type:** convention | **Strength:** strong-consensus
**Recommended action:** Accept as standard / Move to linter

**Evidence** (~2 comments):
> "Our error messages generally start with lowercase letters" — @alexcrichton, PR#14879
> "Instead of `. {}`, could this be `: {}` and all of the messages start with lowercase letters instead of uppercase letters?" — @alexcrichton, PR#14879

**Rationale:** Consistency in terminal output. Standardizing on lowercase makes it easier to embed error messages into wider context strings without awkward capitalization.

### 4. Group Imports at the Top of the File
**Rule:** Avoid per-function or highly localized imports; group `use` statements at the top of the file.
**Category:** Code Structure | **Type:** convention | **Strength:** moderate
**Recommended action:** Accept as standard

**Evidence** (~1 comments):
> "Imports like this are generally against rust style (lots per-function imports), could you add these to the top of the file?" — @alexcrichton, PR#15051

**Rationale:** Centralized imports make dependencies clear at a glance and prevent duplicated or scattered `use` statements across large files.

### 5. Push Failure to the Caller via `Option`
**Rule:** Getter methods (like `get` and `get_mut`) should return `Option` to push out-of-bounds failure handling to the caller, rather than failing internally or returning raw references.
**Category:** API Design | **Type:** principle | **Strength:** strong-consensus
**Recommended action:** Accept as standard

**Evidence** (~2 comments):
> "Should the `get` and `get_mut` methods return `Option<&T>` to push failure towards the client?" — @alexcrichton, PR#14604
> "Agreed, this maps to Python (and maybe other languages too?) and I always found it reasonable there." — @nikomatsakis, PR#14604

**Rationale:** Encourages safe API design. It prevents hidden panics/aborts deep within library functions, forcing consumers to acknowledge and handle empty states or invalid indices.

### 6. Line Length Limits
**Rule:** Restrict lines of code and documentation to a strict character limit.
**Category:** Formatting | **Type:** tooling-rule | **Strength:** contested
**Recommended action:** Needs decision

**Evidence** (~5 comments):
> "Almost all other documentation in rustc is formatted to 80 char width, can you do so here as well?" — @alexcrichton, PR#16156
> "There was a shift long ago from a hard 78-character limit to a hard 100-character limit. Almost all code now uses 80 characters as the limit..." — @alexcrichton, PR#14879
> "100 used to be the recommended figure, but more recently it has become 80." — @chris-morgan, PR#15450
> "Huh? But 100 characters is our defined style." — @chris-morgan, PR#14994
> "I was under that impression too. I'm against touching a few hundred lines without apparent reason!" — @michaelwoerister, PR#14994

**Rationale:** Excessive line lengths degrade readability, especially in split-pane editors or terminal environments.
⚠️ **Conflict:** There is confusion among core contributors regarding whether the official limit is 80 or 100 characters. Reviewers are actively enforcing different limits. 

---
## Conflicts Requiring Human Decision

1. **Maximum Line Length (80 vs 100 characters)**
   * *Flagged in:* Candidate 6
   * *Resolution Question:* Should the project mandate an 80-character limit or a 100-character limit for code and documentation? Once decided, this must be updated in the style guide and enforced via `rustfmt`/`tidy`.

---
## Patterns to Move to Tooling

The following formatting and syntactic preferences have strong consensus but should be enforced by a linter (e.g., `rustfmt` or `clippy`) to avoid wasting human review time:

* **Vector Literals:** Prefer `vec![...]` over `vec!(...)`. 
  *(Evidence: "We predominately try to use `vec![...]` for vector literals." — @alexcrichton)*
* **Indentation:** Use 4-space indentation; absolutely no tabs or 2-space indents. 
  *(Evidence: "rust conventions are to use four-space tabs instead of 2" — @alexcrichton)*
* **Struct Initialization:** Put each field on its own line when initializing structs. 
  *(Evidence: "Prevailing style is to put each field on its own line: Foo { bar: ..., }" — @alexcrichton)*
* **Static Variable Naming:** Use `ALL_CAPS` for static variables. 
  *(Evidence: "Statics stylistically are all-caps" — @alexcrichton)*
* **Trailing Whitespace:** Strip trailing whitespaces. 
  *(Evidence: "Just a small trailing space here." — @alexcrichton)*
* **Spacing around Colons:** Place a space *after* the colon, but not before. 
  *(Evidence: "Conventionally the style is to only have a space after the colon, not before it." — @alexcrichton)*

*(Note on Personal Preferences: One reviewer noted, "I like to align the `|`s with the `=>`s they belong to... But I see that the style guide recommends something entirely different" (@michaelwoerister). This alignment should be strictly left to the formatter to resolve personal style vs. team norms).*

---
## Weak Signals / Insufficient Evidence

The following items were mentioned as conventions or principles but lack enough repetition in the corpus to be codified as widespread rules without further discussion:

* **Avoiding multiple boolean arguments:** "Multiple boolean flags is normally an area of danger" (@alexcrichton). This is a well-known clean code principle, but only appeared once in this sample.
* **Avoiding `super` in module resolution:** "I don't see `super` in the codebase that often, and it's generally frowned upon." (@alexcrichton). 
* **Iterator Naming (`words` vs `word_iter`):** "Our iterator naming conventions indicate this method should be called `words` instead of `word_iter`" (@alexcrichton). Points to a broader, undocumented naming schema.
* **Return Type Arrow Alignment:** "current conventions for a return type on the next line is to line up the arrow with the name of the first argument." (@alexcrichton). Likely belongs in `rustfmt` rather than human guidance.