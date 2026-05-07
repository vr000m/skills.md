# Global Preferences

## Git
- **Never squash merge PRs.** Use regular merge (`gh pr merge --merge --delete-branch`) to preserve individual commit history.
- **Always work on feature branches** — never commit directly to main. Create branch, dev plan, update docs, then PR.

## Commit Hygiene
- **Never use `git add -A`, `git add --all`, or `git add .`** — they sweep untracked scratch/dev-plan files into commits. Stage explicit paths.
- When a multi-step task touches multiple logical changes, split into separate commits with focused scope.

## Pre-Push Checks
- For Python projects: run `ruff format` and `ruff check` before pushing, not just `check`.
- Run the full test suite locally before opening or updating a PR.

## Review Workflow
- **Verify the invariant, not just the tests.** Before declaring a structural fix complete (hashing, dedup, parity, state-machine), state the invariant and show concrete evidence (assertion, diff, log) that it holds across all call sites. Tests passing does not by itself prove the fix is correct.
- After applying review fixes, re-verify the review-marker / plan-file hash before delegating further phases.
- Before running adversarial / Codex / multi-lens review, confirm the diff scope: print `git diff <base>...HEAD --stat` and confirm it matches the feature branch, not the local worktree diff.

## Plan Updates
- When updating a dev plan, grep `docs/dev_plans/` (or equivalent) for sibling plans referencing the same feature/component and update them in the same pass; partial updates leave stale references.

## Tool Output Discipline
- Treat tool output as context budget. Start with narrow probes (`git diff --stat`, `git diff --name-only`, `git log --oneline -N`, `rg -l`, `rg -c`) before reading full diffs or long logs.
- Bound noisy commands with filters or limits: pipe logs through `rg -i "error|fail|warn|traceback|exception"` or `tail -50` when the full output is not needed.
- Prefer terse, structure-aware tools when available: `rg` over recursive grep, `fd` over broad `find`, `jq` for JSON, and `yq` for YAML. Do not grep structured data when a parser is practical.
- Use `multi_tool_use.parallel` for independent reads and searches, with each command already scoped to the smallest useful output.
- Use subagents only when the user explicitly asks for delegation or parallel agent work. Give each agent a bounded output contract and a disjoint scope; keep urgent blocking work local.
- Reuse recently read context within the same turn, but verify freshness before non-trivial edits or claims after user turns, formatter hooks, codegen, git operations, or subagent work. Cheap checks include `git status --short <path>` and an mtime probe.

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

1. `/dev-plan create feature xyz` — Create the plan; on `create` only, runs one Explore step via `spawn_agent` with the configured lower-cost model when available (inline fact-gathering fallback otherwise) that returns structured codebase facts (verified paths, observed patterns, dependency versions, verified git refs) which land above the review marker. `update` and `complete` do not re-explore
2. `/review-plan` — Audit the plan by dispatching four parallel `spawn_agent` lens workers (`architecture`, `sequencing`, `spec-and-testing`, `codebase-claims`) when available, with sequential in-session fallback labelled best-effort isolation; merges findings by severity and blocks until complete. Cost: three high-reasoning lenses plus one lower-cost factual lens per run
3. Address review findings, update plan as needed
4. `/fan-out` — Fan out independent tasks to parallel agents (or implement manually)
5. `/deep-review` — Run the multi-lens review before merge

## Bug Fixing
- When given a bug with clear signals (logs, errors, failing tests), fix it autonomously. Don't ask for hand-holding.

## Code Changes
- **Minimal impact** — only touch what's necessary. Find root causes, no temporary hacks.

## MCP Tools
- When pipecat-context-hub MCP is available, prefer its tools (`search_docs`, `search_api`, `search_examples`, `get_example`, `get_doc`, `get_code_snippet`) for Pipecat framework questions. If unavailable, use normal repository/docs discovery as fallback. Do not read `.venv` source directly unless explicitly requested.
- **Multi-concept queries:** When searching for multiple topics at once, use ` + ` or ` & ` as delimiters (e.g., `search_docs("TTS + STT")`, `search_examples("idle timeout + function calling + Gemini")`). Each concept is searched independently and results are interleaved for balanced coverage. Do NOT stuff multiple concepts into a single natural-language query.

## Security
- Before committing, check staged files for PII, private keys, secrets, and credentials. Never commit these.

## Auto-Memory Hygiene
- When writing a memory file, include a `last_verified: YYYY-MM-DD` field in the frontmatter (today's date).
- Before relying on a memory whose `last_verified` is **>14 days old**, re-verify its top claims against live state (file existence, git tags, branch HEADs) and either refresh `last_verified` or remove the memory.
- Memory snapshots of repo activity (logs, architecture summaries) are frozen in time — for "current state" questions prefer `git log` / live reads over recall.
