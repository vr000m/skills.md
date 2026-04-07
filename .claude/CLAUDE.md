# Global Preferences

## Git
- **Never squash merge PRs.** Use regular merge (`gh pr merge --merge --delete-branch`) to preserve individual commit history.
- **Always work on feature branches** — never commit directly to main. Create branch, dev plan, update docs, then PR.

## Workflow
- Discuss and plan before implementing non-trivial features.
- **If an approach is failing, stop and re-plan** — don't keep pushing on a broken path.
- Update docs (AGENTS.md, README.md, dev plan) alongside code changes, not after.
- Run `/update-docs`, `/review`, `/security-review`, and `/deep-review` before merging.
- Fix all review findings before merge.
- Update PR description to reflect final state of the work.
- **Verify before marking done** — run tests, check logs, demonstrate correctness. Don't claim a task is complete without proof.

## Bug Fixing
- When given a bug with clear signals (logs, errors, failing tests), fix it autonomously. Don't ask for hand-holding.

## Code Changes
- **Minimal impact** — only touch what's necessary. Find root causes, no temporary hacks.

## MCP Tools
- When pipecat-context-hub MCP is available, always prefer its tools (`search_docs`, `search_api`, `search_examples`, `get_example`, `get_doc`, `get_code_snippet`) for Pipecat framework questions. Do not read `.venv` source directly.
- **Multi-concept queries:** When searching for multiple topics at once, use ` + ` or ` & ` as delimiters (e.g., `search_docs("TTS + STT")`, `search_examples("idle timeout + function calling + Gemini")`). Each concept is searched independently and results are interleaved for balanced coverage. Do NOT stuff multiple concepts into a single natural-language query.

## Destructive Operations
- **Never `rm -rf` a data directory without backing it up first** (`cp -a <dir> <dir>.bak`).
- **Check for active writers before deleting** — run `lsof +D <dir>` and verify no process is reading/writing.
- **A snapshot comparison is not enough** — a directory that looks like a duplicate right now may have new files written to it minutes later by a running process.
- **Never overwrite or delete a SQLite database wholesale.** Merge by inspecting entries row by row. Back up first.
- When deleting data files, prefer moving to a `backups/` directory over permanent deletion, so they can be recovered.
- This applies to any runtime data, caches, databases, or directories that could be actively used — not just source code.

## Context Management
After completing a major task (commit, review, PR, skill run), assess the conversation:
- **Mid-task**: "We're mid-implementation on X — let's finish before managing context."
- **More related work remains**: Suggest `/compact focus on [specific next phase]`
- **Work is done or next task is independent**: Suggest `/clear` or provide a self-contained prompt to continue in a new session. Include: the goal, what's done, what's left, relevant file paths, and the branch name.

## Security
- Before committing, check staged files for PII, private keys, secrets, and credentials. Never commit these.
