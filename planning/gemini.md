
  
User  9:16 AM

I'm looking for a candidate github repo to use for some testing, but I am particularly interested in some meta data from PRs etc. Essentially, I want to put together some ideas for using a company's historical discussions and resolutions on a codebase to extract the underlying principles to emphasise to newly onboard devs and as a bible for agentic coding assistants joining the effort. Is there a good candidate repo you're aware of with substantial history and constructive (not bickering) discussion to resolve conflicting standards?

Model  9:16 AM

![Thinking](https://www.gstatic.com/aistudio/watermark/watermark.png)Thoughts

Expand to view model thoughts

chevron_right

This is a brilliant use case. Using historical pull request (PR) data, issue threads, and code reviews as a Retrieval-Augmented Generation (RAG) knowledge base for an agentic coding assistant is one of the most promising frontiers in AI-assisted software engineering. It essentially captures the "tribal knowledge" that is rarely written down in official documentation.

To test this, you need repositories with **high volume**, **strict moderation** (to filter out toxic bickering), **strong architectural opinions**, and **visible evolution of standards**.

Here are the best candidate repositories, categorized by what makes them uniquely suited for your experiment:

### 1. The Gold Standard for Constructive Debate: rust-lang/rust

The Rust community is legendary for its strict adherence to a Code of Conduct and its culture of rigorous, highly polite, and constructive technical debate.

-   **Why it’s perfect:** When standards conflict in Rust, the community uses a structured process to resolve them. You will find incredible PR discussions about memory safety, naming conventions, API ergonomics, and performance tradeoffs.
    
-   **Pro-Tip:** Look at the rust-lang/rfcs (Request for Comments) repository alongside the main rust repo. Mapping an accepted RFC to the PR that implemented it will give your agent an incredible map of Principle -> Discussion -> Execution.
    

### 2. Real-World Application Architecture: microsoft/vscode

If you want your agent to learn about building a standard, large-scale application (rather than a language compiler), VS Code is phenomenal.

-   **Why it’s perfect:** It is a massive TypeScript codebase maintained by a highly disciplined core team at Microsoft, but open to the public. You will find extensive PR discussions about architectural layering, performance optimizations (e.g., avoiding memory leaks in the DOM), and UI/UX standards.
    
-   **What to look for:** Look for PRs involving "debt," "refactoring," or "strictness" where core maintainers explain why a community contribution doesn't fit the VS Code architecture and how to fix it.
    

### 3. The "Framework Philosophy" Model: django/django or rails/rails

Both of these backend frameworks have been around for over 15 years and have a deeply ingrained philosophy ("The Django Way" or "The Rails Way").

-   **Why it’s perfect:** You can track how coding standards have evolved over a decade. Maintainers on these repos are excellent at politely explaining to contributors why a certain PR violates the framework's core design principles (e.g., violating MVC boundaries, or ORM anti-patterns).
    
-   **What to look for:** Django’s PRs often include deep discussions about backward compatibility—a crucial principle for AI agents to understand when modifying existing enterprise codebases.
    

### 4. Paradigm Shifts & UI Standards: facebook/react

React is a great candidate if you want to test how well your system handles changing standards over time.

-   **Why it’s perfect:** React has gone through massive architectural shifts (Class Components -> Functional Components -> Hooks -> Server Components). The PRs and issues around these transitions feature core developers deeply explaining the underlying principles of state management, purity, and rendering lifecycles.
    

----------

### Strategy for Extracting the Data

If you are building a pipeline to extract this data, here is how you can filter the noise to find the "biblical" principles for your agent:

1.  **Filter by Comment Count:** A PR with 1–3 comments is usually a simple bug fix or an easy "LGTM" (Looks Good To Me). A PR with **15 to 50 comments** is your sweet spot for architectural discussion. (PRs with 150+ comments often devolve into bikeshedding).
    
2.  **Target Specific Labels:** Query the GitHub API for PRs with labels like needs-decision, architecture, rfc, discussion, or breaking-change.
    
3.  **Weight "Collaborators" and "Owners":** When parsing the text, give heavily weighted priority to the comments made by users with the MEMBER or OWNER association. Their comments usually contain the resolutions and principles ("We prefer to use X instead of Y here because of Z...").
    
4.  **Extract the Resolution:** Look for the final comments before a PR transitions from Open to Merged or Closed. Often, the PR author will summarize the changes they made to satisfy the reviewer's principles.
    

**How to get the data easily:** Instead of scraping the GitHub API from scratch and hitting rate limits, you can use **GitHub Archive (GHArchive)** or the **GHTorrent** datasets available publicly on Google BigQuery. You can run a SQL query to extract all PR comments from microsoft/vscode over the last 5 years that contain words like "architecture", "prefer", "standard", or "convention" to seed your RAG database instantly.

User  9:18 AM

I was completely unaware of GHArchive and GHTorrent as concepts! Can you give me a bit of background and explain how we could harness them here?

Model  9:18 AM

![Thinking](https://www.gstatic.com/aistudio/watermark/watermark.png)Thoughts

Expand to view model thoughts

chevron_right

If you have ever tried to scrape GitHub using their standard API, you’ve likely hit their aggressive rate limits (usually 5,000 requests per hour). If you are trying to analyze years of pull requests, comments, and code reviews, the API will take weeks to pull the data.

This is where **GHArchive** and **GHTorrent** come in. They are massive, publicly available datasets that allow you to bypass the API entirely and query GitHub's entire history using SQL.

Here is a breakdown of what they are and exactly how you can harness them to build your "agentic coding bible."

----------

### 1. The Background: What are they?

**GHArchive (GitHub Archive)**

-   **What it is:** Every single action taken on public GitHub (a PR opening, a comment, a star, a fork) generates an "Event." GHArchive is a project that constantly monitors GitHub's timeline API, captures every single event as a JSON object, and archives it into hourly files.
    
-   **How to access it:** While you can download the raw JSON files, the magic of GHArchive is that it is mirrored to **Google BigQuery**. You can write SQL to instantly query billions of GitHub events across any public repository.
    
-   **Status:** Highly active. It tracks data up to the current day.
    

**GHTorrent**

-   **What it is:** GHTorrent was a similar project built primarily for academic researchers. Instead of just dumping JSON events, it followed the events, made additional API calls, and built a deeply relational, offline database (e.g., specific SQL tables for users, commits, pull_requests, comments).
    
-   **Status:**  **Mostly deprecated.** It is a fantastic historical dataset, but it struggled to keep up with GitHub's immense scale and largely stopped updating reliably around 2019-2020.
    
-   **Verdict for you:** Ignore GHTorrent and **focus entirely on GHArchive via Google BigQuery.**
    

----------

### 2. How to Harness GHArchive for Your Use Case

To extract the "underlying principles" from PRs, you need to reconstruct the conversation threads where standards clash and are resolved. Here is the exact pipeline you can build.

#### Step 1: Set up Google BigQuery

1.  Go to the Google Cloud Console.
    
2.  Enable BigQuery (you get 1 TB of query data processed for free every month, which is plenty if you are querying specific repos).
    
3.  Add the githubarchive public dataset to your workspace.
    

#### Step 2: Write the SQL to Extract High-Signal Discussions

In GHArchive, you care about three specific event types:

-   PullRequestEvent: When a PR is opened, closed, or merged.
    
-   IssueCommentEvent: General comments on the PR thread.
    
-   PullRequestReviewCommentEvent: Comments attached to specific lines of code in the PR diff.
    

Here is an example SQL query you could run in BigQuery right now to extract the exact data you want from a repo like microsoft/vscode or rust-lang/rust:

codeSQL

```
SELECT
  repo.name AS repository,
  JSON_EXTRACT_SCALAR(payload, '$.issue.number') AS pr_number,
  JSON_EXTRACT_SCALAR(payload, '$.comment.user.login') AS author,
  JSON_EXTRACT_SCALAR(payload, '$.comment.author_association') AS role, -- e.g., 'MEMBER', 'OWNER', 'CONTRIBUTOR'
  JSON_EXTRACT_SCALAR(payload, '$.comment.body') AS comment_text,
  created_at
FROM
  `githubarchive.year.2023` -- (Or whatever year you want)
WHERE
  repo.name = 'rust-lang/rust'
  AND type IN ('IssueCommentEvent', 'PullRequestReviewCommentEvent')
  -- Filter for core team members to get authoritative standards
  AND JSON_EXTRACT_SCALAR(payload, '$.comment.author_association') IN ('MEMBER', 'OWNER')
  -- Filter for comments likely containing architectural feedback
  AND (
    LOWER(JSON_EXTRACT_SCALAR(payload, '$.comment.body')) LIKE '%prefer%' OR
    LOWER(JSON_EXTRACT_SCALAR(payload, '$.comment.body')) LIKE '%convention%' OR
    LOWER(JSON_EXTRACT_SCALAR(payload, '$.comment.body')) LIKE '%anti-pattern%' OR
    LOWER(JSON_EXTRACT_SCALAR(payload, '$.comment.body')) LIKE '%architecture%'
  )
ORDER BY
  pr_number, created_at;
```

#### Step 3: Group by PR and Reconstruct the Thread

Once you run that query, export the results as a CSV or JSON file. Now you have a manageable, highly-filtered dataset of core-maintainer comments.

Write a quick Python script to group these comments by pr_number. This reconstructs the "discussion."

#### Step 4: Use an LLM to Extract the "Principles" (The RAG Pipeline)

Raw comments are too messy to feed directly to an agent as rules. You need to distill them. You can write a script that passes each reconstructed PR thread to an LLM (like GPT-4o or Claude 3.5 Sonnet) with a prompt like this:

> "You are an expert software architect analyzing a historical pull request discussion from the VS Code repository. Read the following comment thread between contributors and core maintainers.  
> 1. What was the code author trying to do?  
> 2. What principle, standard, or architectural rule did the core maintainer enforce?  
> 3. Explain the "Why" behind this rule based on the maintainer's explanation.  
> Output this as a structured JSON object containing 'principle_name', 'description', 'bad_example', and 'good_example'."

#### Step 5: Build the "Bible"

Now, instead of a massive database of messy PRs, you have a distilled JSON array of **company-specific architectural principles**.

-   **For human onboarding:** Generate a Markdown document summarizing these principles. (e.g., "How we handle State Management in VS Code").
    
-   **For the AI Agent:** Embed these JSON objects into a Vector Database. When your agentic coding assistant is asked to write a new feature, it first queries the Vector DB: "What are the historical standards for doing X in this codebase?" The DB returns the exact principles the core maintainers fought for 3 years ago, and the agent writes code that complies perfectly with the repo's unwritten rules.
    

### Quick Warning on BigQuery Costs

GHArchive is massive (terabytes per year). **Do not** run a query without a WHERE repo.name = '...' clause, or you will scan the whole dataset and eat up your free tier instantly. Always partition your queries by year or month (e.g., `githubarchive.month.202301`) when testing!