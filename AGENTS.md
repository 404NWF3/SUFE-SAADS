# AGENTS.md

Repository guidance for agentic coding tools operating in `E:\@4C-2026\SUFE-SAADS`.

This file is intentionally practical and repository-specific.

## Scope

- Primary codebase areas:
  - `backend/agents/intel_agents/` for WP1-1 orchestration, collectors, tools, schemas, services
  - `backend/db/` for DB DTOs, repositories, services, and unit-of-work patterns
  - `tests/wp11/` for current WP1-1 tests
  - `docs/` for architecture and planning documents
- Main runtime stack:
  - LangChain
  - LangGraph
  - CrewAI-compatible collaboration layer
  - Pydantic v2
  - `httpx`
  - PostgreSQL access via project DB layer

## Rules Files

- No `.cursor/rules/` directory was found.
- No `.cursorrules` file was found.
- No `.github/copilot-instructions.md` file was found.
- If any of those files are added later, treat them as higher-priority repository guidance and update this file.

## Environment and Tooling

- Package manager / runner: `uv`
- Python requirement: `>=3.10` in `pyproject.toml`
- Important note for tests:
  - Prefer `uv run python -m pytest ...`
  - Do not rely on `uv run pytest ...` if local PATH may resolve a global `pytest.exe`

## Install Commands

- Create / sync environment:
```bash
uv sync
```

- Install dev dependencies if needed:
```bash
uv sync --extra dev
```

- If the environment is already created but `pytest` is missing, re-sync with dev extras.

## Run Commands

- Run a Python module in repo env:
```bash
uv run python -c "print('ok')"
```

- Run a WP1-1 runtime smoke check:
```bash
uv run python -c "from agents.intel_agents.orchestrator.runtime import Phase1GraphRuntime; r=Phase1GraphRuntime(); out=r.invoke_stub_run(); print(out['run_status'])"
```

## Test Commands

- Run all WP1-1 tests:
```bash
uv run python -m pytest tests/wp11 -v
```

- Run a single test file:
```bash
uv run python -m pytest tests/wp11/test_phase1_runtime.py -v
```

- Run a single test function:
```bash
uv run python -m pytest tests/wp11/test_phase1_runtime.py -v -k test_phase1_stub_run_succeeds
```

- Run Phase 2 tests only:
```bash
uv run python -m pytest tests/wp11/test_phase2_sources.py -v
```

- Run Phase 3 tests only:
```bash
uv run python -m pytest tests/wp11/test_phase3_standardization.py -v
```

- Run parallel / Crew coordination tests:
```bash
uv run python -m pytest tests/wp11/test_phase1_parallel_and_crews.py -v
```

## Lint / Format Commands

- No dedicated formatter or linter is configured in `pyproject.toml` right now.
- Before introducing a new tool such as `ruff`, `black`, or `mypy`, do not assume it is project-standard.
- In the absence of configured tooling:
  - keep formatting consistent with surrounding code
  - keep imports stable and readable
  - keep type annotations explicit where the codebase already uses them
  - avoid broad stylistic rewrites

## Build Commands

- No packaging build pipeline is currently defined.
- If a build artifact is needed, verify first whether the task is really a test/run task rather than a package build task.

## Repository Conventions

## Imports

- Prefer standard library imports first, then third-party, then local imports.
- Separate import groups with one blank line.
- Use relative imports inside `backend/agents/intel_agents/` when following existing local package structure.
- Use project package imports inside `backend/db/` consistently with the existing module style.
- Do not introduce wildcard imports.

## Formatting

- Follow existing style in nearby files.
- Use 4 spaces for indentation.
- Keep line lengths readable; wrap long calls across multiple lines.
- Prefer trailing commas in multi-line literals / calls when already used nearby.
- Keep docstrings short and functional.

## Types

- Add type annotations for public functions, service methods, DTOs, and non-trivial helpers.
- Prefer `TypedDict` or Pydantic DTOs for structured state or payloads.
- Prefer `dict[str, Any]` only at boundaries where the system is intentionally flexible.
- If a patch/update object crosses node boundaries, validate it through a DTO rather than passing arbitrary dicts.
- Preserve `Literal` types and constrained fields where already defined.

## Naming

- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- DTO / schema classes use `*DTO`
- LangGraph node functions use `*_node`
- Services use `*Service`
- Agents use `*Agent`

## Error Handling

- Fail explicitly; do not silently swallow exceptions unless the fallback is intentional and observable.
- If a fallback occurs, record it in structured output or audit metadata.
- Preserve repository patterns such as:
  - `NotFoundError`
  - `DatabaseError`
  - typed error/audit records
- Keep retry behavior explicit.
- Distinguish retryable vs non-retryable failures where possible.

## State and Graph Rules

- LangGraph state should favor IDs, refs, summaries, and stats over large payload bodies.
- Do not put raw payload blobs directly into long-lived graph state unless unavoidable.
- For concurrent graph branches, use merge-safe annotated state fields.
- Avoid adding last-value state keys that can be written by multiple parallel nodes in the same step.
- If a node returns a patch, keep it minimal and typed.

## Source Collection Rules

- Treat source adapters as source-specific contracts, not generic scraping hacks.
- Preserve pagination, auth, retry, backoff, circuit-breaker, and audit metadata when changing adapters.
- Keep `query_run_id` attached to raw records.
- Preserve fetch audits and ingest audits.
- Do not remove degraded / hybrid mode visibility.

## Standardization Rules

- Keep rule-based extraction available even when LLM enhancement exists.
- `llm_optional` must degrade safely when credentials are unavailable.
- Prefer fusion of rules + LLM over hard overwrite.
- Preserve:
  - `field_confidence`
  - `conflict_flags`
  - `validation_findings`
  - `normalization_trace`
  - `extraction_reason`

## DB Layer Rules

- Use the project `UnitOfWork` and repository/service abstractions.
- Do not write ad hoc SQL in agent/orchestrator code.
- Prefer transactional boundaries in the DB service layer.
- When integrating new sources, keep source names aligned with DB `intel_source` rows when possible.

## Testing Expectations

- Add or update tests for behavior changes.
- For graph/orchestration changes, include at least one smoke-path test.
- For source changes, test stub mode first.
- For resume / recover changes, test failure then recovery.
- For standardization changes, test schema shape plus at least one semantic assertion.

## Change Strategy for Agents

- Make targeted changes, not repo-wide rewrites.
- Preserve docs and tests when updating architecture behavior.
- Prefer additive changes over destructive refactors unless clearly necessary.
- If you discover a gap between code and docs, fix code first, then update docs if requested or clearly needed.

## Quick Checklist Before Finishing

- Did you use `uv run python -m pytest ...` for tests?
- Did you avoid introducing unconfigured tooling assumptions?
- Did you preserve typed DTO/state boundaries?
- Did you keep graph parallel writes merge-safe?
- Did you keep fallback paths observable?
- Did you avoid breaking stub mode?
