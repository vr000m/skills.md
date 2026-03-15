# Global Preferences

## Git
- **Never squash merge PRs.** Use regular merge (`gh pr merge --merge --delete-branch`) to preserve individual commit history.
- **Always work on feature branches** — never commit directly to main. Create branch, dev plan, update docs, then PR.

## Workflow
- Discuss and plan before implementing non-trivial features.
- **If an approach is failing, stop and re-plan** — don't keep pushing on a broken path.
- Update docs (AGENTS.md, README.md, dev plan) alongside code changes, not after.
- Run pre-merge documentation, code-review, and security-review checks before merging.
- Prefer the local Codex skills/workflows for these checks when available (for example, `update-docs`); if unavailable, run an equivalent manual audit and report findings.
- Fix all review findings before merge.
- Update PR description to reflect final state of the work.
- **Verify before marking done** — run tests, check logs, demonstrate correctness. Don't claim a task is complete without proof.

## Skill Workflow

Recommended development workflow using skills:

1. `/dev-plan create feature xyz` — Create the plan
2. `/review-plan` — Audit plan for gaps and undocumented assumptions (blocks until complete)
3. Address review findings, update plan as needed
4. `/fan-out` — Fan out independent tasks to parallel agents (or implement manually)

## Bug Fixing
- When given a bug with clear signals (logs, errors, failing tests), fix it autonomously. Don't ask for hand-holding.

## Code Changes
- **Minimal impact** — only touch what's necessary. Find root causes, no temporary hacks.

## MCP Tools
- When pipecat-context-hub MCP is available, prefer its tools (`search_docs`, `search_api`, `search_examples`, `get_example`, `get_doc`, `get_code_snippet`) for Pipecat framework questions. If unavailable, use normal repository/docs discovery as fallback. Do not read `.venv` source directly unless explicitly requested.
- **Multi-concept queries:** When searching for multiple topics at once, use ` + ` or ` & ` as delimiters (e.g., `search_docs("TTS + STT")`, `search_examples("idle timeout + function calling + Gemini")`). Each concept is searched independently and results are interleaved for balanced coverage. Do NOT stuff multiple concepts into a single natural-language query.

## Security
- Before committing, check staged files for PII, private keys, secrets, and credentials. Never commit these.
