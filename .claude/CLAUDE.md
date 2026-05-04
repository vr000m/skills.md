# Global Preferences

## Git
- **Never squash merge PRs.** Use regular merge (`gh pr merge --merge --delete-branch`) to preserve individual commit history.
- **Always work on feature branches** — never commit directly to main. Create branch, dev plan, update docs, then PR.

## Commit Hygiene
- **Never use `git add -A`, `git add --all`, or `git add .`** — they sweep untracked scratch/dev-plan files into commits. A PreToolUse hook blocks these. Stage explicit paths.
- When a multi-step task touches multiple logical changes, split into separate commits with focused scope.

## Pre-Push Checks
- For Python projects: run `ruff format` AND `ruff check` before pushing — not just `check`. (A PostToolUse hook auto-formats on Edit/Write, but verify before push.)
- Run the full test suite locally before opening or updating a PR.

## Review Workflow
- **Verify the invariant, not just the tests.** Before declaring a structural fix complete (hashing, dedup, parity, state-machine), state the invariant and show concrete evidence (assertion, diff, log) that it holds across all call sites. Tests passing ≠ fix correct.
- After applying review fixes, re-verify the review-marker / plan-file hash before delegating further phases.
- Before running adversarial / Codex / multi-lens review, confirm the diff scope: print `git diff <base>...HEAD --stat` and confirm it matches the feature branch, not the local worktree diff.

## Plan Updates
- When updating a dev plan, grep `docs/dev_plans/` (or equivalent) for sibling plans referencing the same feature/component and update them in the same pass — partial updates leave stale references.

## Workflow
- Discuss and plan before implementing non-trivial features.
- **If an approach is failing, stop and re-plan** — don't keep pushing on a broken path.
- Update docs (AGENTS.md, README.md, dev plan) alongside code changes, not after.
- Run `/update-docs`, `/review`, `/security-review`, and `/deep-review` before merging.
- Fix all review findings before merge.
- Update PR description to reflect final state of the work.
- **Verify before marking done** — run tests, check logs, demonstrate correctness. Don't claim a task is complete without proof.

## Long-running Processes
- **Always pair background processes with a Monitor.** When starting any long-running process (dev server, ngrok, docker compose, log tail, background worker), run it with `Bash(run_in_background)` and immediately set up a `Monitor` on its output filtered for errors/warnings. This way the user can interact with the process (e.g., test in a browser) while Claude stays aware of server-side issues.
- Filter Monitor output: `grep --line-buffered -E "ERROR|WARN|Traceback|Exception|FATAL|panic"` — don't stream raw logs.

## Permissions
- Permissions are configured in `~/.claude/settings.local.json` with a broad allow list and explicit deny list (`rm`, `git rm`, `git merge`, `git reset --hard`, `git clean`, `git push --force`, package uninstalls, container deletion, `gh repo delete`, `gh pr close`).
- **Goal:** Claude should run long/overnight implementation tasks without permission prompts for non-destructive ops.
- If a safe command prompts during an autonomous run, note it — it should probably be added to the allow list.
- User has a `riskyclaude` alias for `claude --dangerously-skip-permissions` but rarely uses it. Do not suggest it.

## Bug Fixing
- When given a bug with clear signals (logs, errors, failing tests), fix it autonomously. Don't ask for hand-holding.

## Code Changes
- **Minimal impact** — only touch what's necessary. Find root causes, no temporary hacks.

## MCP Tools
- When pipecat-context-hub MCP is available, always prefer its tools (`search_docs`, `search_api`, `search_examples`, `get_example`, `get_doc`, `get_code_snippet`) for Pipecat framework questions. Do not read `.venv` source directly.
- **Multi-concept queries:** When searching for multiple topics at once, use ` + ` or ` & ` as delimiters (e.g., `search_docs("TTS + STT")`, `search_examples("idle timeout + function calling + Gemini")`). Each concept is searched independently and results are interleaved for balanced coverage. Do NOT stuff multiple concepts into a single natural-language query.

## Destructive Operations
Destructive commands are blocked by the permissions deny list — they will prompt. When the prompt appears, apply these rules before approving:
- **Back up first.** Never `rm -rf` a data directory without `cp -a <dir> <dir>.bak`. Prefer moving to a `backups/` directory over permanent deletion.
- **Check for active writers** with `lsof +D <dir>` before deleting — a directory that looks like a duplicate may have a running process writing to it. A snapshot comparison is not enough.
- **SQLite databases:** never overwrite or delete wholesale. Merge row by row, always back up first.
- Applies to runtime data, caches, and databases — not just source code.

## Context Management
After completing a major task (commit, review, PR, skill run), assess the conversation:
- **Mid-task**: "We're mid-implementation on X — let's finish before managing context."
- **More related work remains**: Suggest `/compact focus on [specific next phase]`
- **Work is done or next task is independent**: Suggest `/clear` or provide a self-contained prompt to continue in a new session. Include: the goal, what's done, what's left, relevant file paths, and the branch name.

## Security
- Before committing, check staged files for PII, private keys, secrets, and credentials. Never commit these.

## Auto-Memory Hygiene
- When writing a memory file, include a `last_verified: YYYY-MM-DD` field in the frontmatter (today's date).
- Before relying on a memory whose `last_verified` is **>14 days old**, re-verify its top claims against live state (file existence, git tags, branch HEADs) and either refresh `last_verified` or remove the memory. Stale memories caused real friction (e.g., trusting a 32-day-old roadmap; assuming v0.0.18 was tagged when it wasn't).
- Memory snapshots of repo activity (logs, architecture summaries) are frozen in time — for "current state" questions prefer `git log` / live reads over recall.
