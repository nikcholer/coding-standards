# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `harvester/` and `synthesiser/`. `harvester/` contains the GitHub API client, search/splitting logic, fetch routines, storage helpers, and the `python -m harvester` entry point. `synthesiser/` builds LLM prompt artifacts from harvested JSONL input via `python -m synthesiser`.

Planning material is kept in `planning/`. Generated outputs live under `data/`: `data/raw/` for harvested JSONL and `data/synthesised/` for prompt files. Keep generated data out of commits unless it is an intentional demo artifact such as `data/synthesised/LLMOutput/`.

## Build, Test, and Development Commands
Install dependencies:

```bash
pip install -r requirements.txt
```

Run the harvester:

```bash
python -m harvester
```

This reads `GITHUB_TOKEN`, uses settings from `harvester/config.py`, and writes JSONL files to `data/raw/`.

Build synthesis prompts:

```bash
python -m synthesiser
```

This reads harvested comments and writes prompt `.json` and `.md` files to `data/synthesised/`.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation, standard-library-first imports, and descriptive snake_case names for functions, variables, and modules. Preserve the current style: small focused modules, dataclasses where helpful, and short docstrings on entry points or non-obvious routines. Prefer `Path` over stringly-typed paths.

## Testing Guidelines
There is no formal automated test suite yet. For changes, verify the relevant entry point directly:

```bash
python -m harvester
python -m synthesiser
```

When adding tests, use `pytest`, place them in `tests/`, and name files `test_*.py`. Favor small fixture-driven tests around sampling, config loading, and JSONL writing.

## Commit & Pull Request Guidelines
Recent commits use short imperative subjects such as `Fix YAML front matter warning in sample output` and `Add sample LLM output...`. Keep commits focused and message subjects concise.

Pull requests should explain the pipeline stage affected, note any config or data-shape changes, and include before/after examples when output files change. Link related issues if present, and call out whether generated artifacts were intentionally included.

## Security & Configuration Tips
Do not commit `.env`, tokens, or harvested private data. Use `.env.example` as the template, set `GITHUB_TOKEN` locally, and review `.gitignore` before adding any new output directories.
