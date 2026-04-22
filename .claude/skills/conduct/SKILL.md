---
name: conduct
description: Walks a reviewed dev-plan phase by phase and delegates each phase's implementation, testing, and fix loop to clean-context subagents. Main Claude stays in a conductor role so context does not exhaust during multi-phase execution. Use when the user says "step through plan", "walk phases", "delegate phase implementation", "conduct plan", "run the plan", or invokes this skill directly with a dev-plan path.
argument-hint: "[path/to/plan.md] [--resume] [--status] [--pause-phase] [--abort-run] [--test-cmd CMD] [--test-timeout SECS] [--max-iterations N]"
---

# Conduct: Phased Delegation for Linear Implementation

Walk a reviewed dev-plan phase by phase. For each phase, spawn clean-context subagents (implementer + test-writer, and optionally a lightweight reviewer) to do the work. The conductor — main Claude running this skill — only reads structured JSON reports, routes failures through a bounded fix loop, commits at phase boundaries, and hands back to the user between phases.

Subagent prompt templates live alongside this file:

- `implementer-prompt.md`
- `test-writer-prompt.md`
- `reviewer-prompt.md`

## Delegation Pattern

Delegation depth from this skill is exactly 1: conduct → workers. Workers never spawn further subagents. This skill is invoked directly by the user as a top-level skill, OR inside a subprocess spawned by `/fan-out` that re-baselines depth at the process boundary. It is never invoked as an `Agent` subagent.

Subagents are spawned via the `Agent` tool with `subagent_type: general-purpose`. Shared workspace — worktree isolation is the user's concern at the outer layer. Clean context comes from the `Agent` tool's default behaviour (no parent conversation history), not from filesystem separation.

## Invocation

```
conduct <plan-path>
conduct --resume <plan-path>
conduct --status <plan-path>
conduct --pause-phase <plan-path>
conduct --abort-run <plan-path>
```

### CLI flags

| Flag | Purpose |
|------|---------|
| `--resume` | Resume after a handback. Reads state, picks up at the next unfinished phase. |
| `--status` | Print the state file contents and exit. No git ops. |
| `--pause-phase` | `git stash push -u -m "conduct-pause-phase-<N>"`, mark phase as user-paused, exit. State lives; `--resume` picks up. |
| `--abort-run` | Delete the state file. No git ops, no stash. The more-destructive flag has the more-explicit name. |
| `--test-cmd CMD` | Override the phase's `Test command:` slot and any repo default. |
| `--test-timeout SECS` | Wall-clock cap on the test-runner subprocess. Default 300. |
| `--max-iterations N` | Fix-loop cap. Default 3. |

## Preflight

Before any phase runs, validate:

### 1. Plan path resolution

- If an argument is provided, use it.
- Else scan `docs/dev_plans/` for the most recently modified `.md` and use that.
- If no plan is found, tell the user and exit.

### 2. Review marker check

The plan MUST end with a trailing marker footer written by `/review-plan` after user acceptance:

```
<!-- reviewed: YYYY-MM-DD @ <sha1> -->
```

- Only the final non-empty line is checked, matched against regex `^<!-- reviewed: \d{4}-\d{2}-\d{2} @ [0-9a-f]{40} -->\s*$`. Marker-shaped text elsewhere in the plan (inside prose or code fences) is ignored.
- Recompute the plan's content hash: take the plan with its final line removed if that final line matched the marker regex (otherwise the plan as-is), write to a temp file, run `git hash-object <tmpfile>`. Compare to the SHA recorded in the marker.
- If marker absent OR hash mismatches → hard-stop with: `Run: /review-plan <plan-path>` and exit.

### 3. Pre-commit health check

Run the repo's pre-commit / lint in non-fix mode on the current tree, in this order: `pre-commit run --all-files`, then `make lint`, then `npm run lint`, then `ruff check .`. If none exist, skip. If the check fails → hard-stop with: `Tree has pre-existing lint/hook failures; fix them before running /conduct`.

This prevents subagent fix-loops from chasing issues they didn't introduce.

### 4. State file load

`<repo-root>/.conduct/state-<plan-basename>.json`, where repo-root comes from `git rev-parse --show-toplevel`.

- If present and `--resume`: load and continue from `phase_index`.
- If present without `--resume`: warn, print state summary, suggest `--resume` or `--abort-run`, exit.
- If absent: initialise with `base_sha = git rev-parse HEAD`, `phase_index = 0`, `status = "running"`.

Acquire an advisory lock on `.conduct/state-<plan-basename>.json.lock` before any write (see `lock.py` shipped with this skill).

### 5. Phase parsing

Parse phases from the `## Implementation Checklist` section with regex:

```
^###\s+Phase\s+(\S+)\s*:\s*(.+?)\s*(\([^)]*\))?\s*$
```

Captures the phase label (e.g. `3` or `3a`) and title; strips trailing parenthesised annotations. Skip phases whose task checkboxes are all `- [x]`. Record each phase's 0-based document position (used as `phase_position` in reports) and verbatim label (used as `phase_label`).

## Per-Phase Workflow

For each unfinished phase, execute steps 1–9. Acquire the state-file lock before any state mutation.

### Step 1 — Parse phase contract

From the phase block, extract:

- `**Impl files:**` — comma-separated paths, globs allowed.
- `**Test files:**` — comma-separated paths, globs allowed.
- `` **Test command:** `<cmd>` `` — parsed with `^\*\*Test command:\*\*\s+\x60([^\x60]+)\x60\s*$`; first match wins; additional matches emit a warning.

Any slot may be absent; see Fallbacks below.

### Step 2 — Parallel vs sequential decision

- If `Impl files:` and `Test files:` resolve to disjoint paths → parallel spawn.
- If they overlap (same file, or one is a subpath of the other) → sequential (implementer first, then test-writer).
- If either slot is missing → sequential (safe default).

Log the decision in the phase summary: `Spawn strategy: parallel` or `Spawn strategy: sequential (reason: file overlap | missing slot)`.

### Step 3 — Fill and spawn subagent prompts

Read `implementer-prompt.md`, extract the fenced ` ``` ` Template block, substitute placeholders:

| Placeholder | Value | JSON type concern |
|-------------|-------|-------------------|
| `{{PLAN_PATH}}` | absolute path | string |
| `{{PHASE_INDEX}}` | phase's 0-based position | substitute bare int (no quotes) |
| `{{PHASE_LABEL}}` | verbatim heading label | substitute JSON-escaped string |
| `{{PHASE_TITLE}}` | verbatim heading title | string (appears in prose, not JSON) |
| `{{ITERATION}}` | current fix-loop iteration | substitute bare int (no quotes) |
| `{{BASE_SHA}}` | `git rev-parse HEAD` at phase start | string |
| `{{PRIOR_DIFF}}` | staged diff from previous attempt, else empty | string |
| `{{TEST_FAILURES}}` | test-runner or pre-commit hook output, else empty | string |

Same pattern for `test-writer-prompt.md` (placeholders: plan path, phase index, phase label, phase title, base sha, existing-tests summary) and `reviewer-prompt.md` (plan path, phase index, phase label, phase title, diff).

Spawn via the `Agent` tool, `subagent_type: general-purpose`, with the filled template as the full prompt. Do not thread parent conversation context. In parallel mode, issue both Agent tool calls in a single message.

### Step 4 — Await both, parse reports

Each subagent returns a final fenced ` ```json ` block. Parse rules:

- **Anchor on the LAST fenced `json` block** in the output, not the first. The plan or prompt body may contain schema examples; only the terminal block is the report.
- Validate against the role schema (required keys: `role`, `phase_position`, `phase_label`, `iteration` for impl/test roles; role-specific fields; `flags` object).
- If the block is missing or fails schema validation → set `state.status = "schema_error"`, record which subagent failed and the raw output tail in state, handback to the user. Do NOT respawn. A clean-context respawn cannot consume "your last output was malformed" because the fresh subagent has no memory of the prior attempt.

### Step 5 — Run tests

Resolve the test command in order:

1. `--test-cmd` CLI flag.
2. Phase's `**Test command:**` line.
3. Repo default: `package.json` `scripts.test`, `pyproject.toml` `[tool.pytest.ini_options]`, or `Makefile` `test` target.
4. None available → emit warning, skip tests, set `state.last_summary` with the skip flag, proceed directly to Step 8 (commit boundary).

Run the resolved command wrapped in `timeout <secs> <cmd>` (`--test-timeout`, default 300). Detect the timeout binary: `timeout` on Linux, `gtimeout` on macOS via Homebrew coreutils. If neither is available, warn and run without wall-clock enforcement.

On non-zero exit → Step 6. On zero exit → Step 7.

### Step 6 — Fix loop (bounded at N = `--max-iterations`, default 3)

No classifier. On any failure (test failure OR pre-commit hook failure at the boundary commit in Step 8):

- Increment `state.iteration_count`. Persist state immediately (crash recovery).
- If `iteration_count > N`: set `state.status = "blocked"`, handback with message `Phase <label> stalled after <N> iterations; see .conduct/state-<plan>.json for diff and failure history.` Do not auto-advance.
- Else respawn the implementer with `{{ITERATION}}` = new count, `{{PRIOR_DIFF}}` = staged diff from previous attempt, `{{TEST_FAILURES}}` = full runner output (or hook output, if the failure came from the boundary commit).
- Exception: if the previous implementer report set `flags.test_contract_mismatch: true`, respawn the **test-writer** instead on this iteration, same inputs. Reset the flag handling for the iteration after that (respawn implementer again unless the next report flips the flag again).

### Step 7 — Optional mid-phase reviewer (one-shot)

Trigger conditions: staged diff > 200 lines, OR > 3 files touched, OR phase tagged high-risk in the plan's Review Focus section. If triggered, spawn one reviewer subagent using `reviewer-prompt.md` with `{{DIFF}}` = staged diff. Log findings into the phase summary. Never loop the reviewer. Findings do not block phase completion — the conductor is advisory here, not gating.

### Step 8 — Phase-boundary commit

After tests pass (or were skipped with warning):

1. **Rogue-commit check.** Compare `git rev-parse HEAD` to `state.base_sha` (for phase 1) or the last completed phase's `commit_sha`. If HEAD advanced, a subagent committed despite the prompt directive. Do NOT stack another commit. Record `rogue_commit_sha` in the phase summary, set `state.status = "awaiting_user"` with a warning, handback.
2. Otherwise run `git commit -m "conduct: phase <label> — <phase title>"`. Commit author = current git user (no impersonation).
3. If the pre-commit hook fails, route the hook output back into Step 6 as a fix-loop iteration. Do NOT use `--no-verify`.
4. On success, record the new `HEAD` SHA in `state.completed_phases[*].commit_sha`.

### Step 9 — Handback

At every phase boundary:

1. Print a structured phase summary:
   - Phase label and title
   - Files changed
   - Spawn strategy (parallel | sequential)
   - Test result (passed | skipped-with-warning)
   - Iterations used
   - Mid-phase reviewer findings if any
   - Any warnings (rogue commit, missing test command, skipped tests)
2. Print the literal next command, on its own line:
   ```
   Run: /conduct --resume <plan-path>
   ```
3. Set `state.status = "awaiting_user"`, persist, release lock, exit the skill.

No keyword heuristic watches for "proceed" — the user copies the printed command when ready.

## Fallbacks

- Missing `Impl files:` / `Test files:` → sequential spawn (Step 2).
- Missing `Test command:`, no repo default, no `--test-cmd` → warn, skip tests for the phase, flag in handback summary (Step 5).
- Missing Testing Notes entirely → same as above; phase completes on implementer-only success with the skip flag.
- Plan has zero unfinished phases → print `All phases complete` and exit.

## State File

Path: `<repo-root>/.conduct/state-<plan-basename>.json`. `.conduct/` is git-ignored (Phase 5).

Schema:

```json
{
  "plan_path": "docs/dev_plans/20260422-feature-conduct-skill.md",
  "plan_content_hash": "<sha1 of plan with marker stripped>",
  "base_sha": "<git sha before phase 1>",
  "phase_index": 3,
  "current_phase_title": "...",
  "completed_phases": [
    { "index": 1, "label": "1", "title": "...", "commit_sha": "...", "tests": "passed", "iterations": 1 }
  ],
  "last_summary": "...",
  "iteration_count": 0,
  "status": "awaiting_user | running | blocked | schema_error | complete",
  "blocker": null
}
```

### Locking

- Primary: `lock.py` acquires `fcntl.flock` on `<state-file>.lock` fd.
- Fallback if Python is unavailable: atomic `mkdir <state-file>.lockdir`.
- Stale locks older than 1 hour are broken with a warning.
- `flock(1)` is NOT used — unavailable by default on macOS.
- Two `/conduct` invocations on the same plan in the same worktree race on the same lock. Sibling worktrees resolve to distinct repo-roots via `git rev-parse --show-toplevel` and therefore distinct state files.

## Known Limitations

- **No agent wall-clock timeout.** The `Agent` tool is synchronous within the parent turn and exposes no PID, so `--agent-timeout` is not enforceable in v1. Mitigated by the fix-loop cap plus explicit iteration counts in prompts. Test-runner timeout is real because the test command is a subprocess.
- **Rogue commits are detected, not prevented.** Subagents are instructed to stage only; a subagent that runs `git commit` anyway is caught by the HEAD-comparison check in Step 8, flagged in state, and handed back to the user rather than auto-corrected.
- **Schema errors do not retry.** A subagent that emits malformed JSON triggers `schema_error` status and immediate handback. The user decides whether to adjust the prompt template or re-invoke.

## Integration Points

- **Plan format**: `/dev-plan` owns the template. Phases need `**Impl files:**`, `**Test files:**`, and `` **Test command:** `<cmd>` `` slots.
- **Review marker**: `/review-plan` writes the marker footer after user acceptance. This skill consumes it as the readiness signal.
- **Fan-out**: a `/fan-out`-spawned Claude subprocess may invoke `/conduct` as its top-level skill; `/conduct` itself does not fan out.
