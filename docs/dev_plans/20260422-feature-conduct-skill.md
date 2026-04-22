# Task: `conduct` skill — phased delegation for linear implementation

**Status**: In Progress
**Assigned to**: Claude (implementation), user (review gates)
**Priority**: Medium
**Branch**: `feature/conduct-skill`
**Created**: 2026-04-22
**Completed**:

## Objective

Add a new skill, `/conduct`, that walks a reviewed dev-plan phase by phase and delegates each phase's implementation, testing, and fix loop to clean-context subagents. Main Claude stays in a conductor role — only reading structured reports and routing failures — so that context does not exhaust during multi-phase execution.

## Context

Users hit a recurring pattern: implementation starts, context fills at ~15–20 %, Claude emits a handoff prompt, the user `/compact`s or `/clear`s, and the next Claude restarts cold. The heavy reading and editing should not live in the main thread. `fan-out` already parallelises *independent* tasks across worktrees; the gap is the common case — a linear multi-phase plan where phases depend on each other but within a phase the work is small. `/conduct` fills that gap by spawning one implementer + one test-writer per phase with clean context (the `Agent` tool's default), looping on failure, and pausing at phase boundaries for user-initiated review or manual testing.

Claude-only skill. Not mirrored to `.codex/skills/`. Codex equivalence will be assessed separately.

This plan was shaped by three `/review-plan` cycles. v1 → v2 resolved worktree-isolation, codex-mirror, intra-phase fan-out, depth-invariant framing. v2 → v3 resolved fix-loop classifier, file-overlap heuristic, test-command format, handback signalling, stale-marker detection, subagent report schema, timeouts, commit-hook recovery, self-host bootstrapping. v3 → v4 (current) resolves the `/review-plan` contract conflict, macOS `flock` availability, hash-strip regex safety, retry-with-clean-context paradox, aspirational timeouts, stage-only enforcement, and Phase 1 verification circularity.

**Implementation ownership.** Phases 1–5 are implemented by hand (or with existing skills like `/dev-plan`, `/fan-out`). Phase 6 is the first time `/conduct` runs on anything — including itself. Phase 7 (docs) must land before PR regardless of how many iterations Phase 6 takes.

## Requirements

### Invocation contract

- `/conduct` is invoked directly by the user as a top-level skill, OR inside a `fan-out`-spawned Claude subprocess. It is NEVER invoked as an `Agent` subagent. The subprocess boundary in `fan-out.sh` re-baselines depth, so `fan-out → conduct → {implementer, test-writer}` is allowed.
- Delegation depth from a `/conduct` invocation is 1: conduct → workers. Workers never spawn.
- Intra-phase fan-out is explicitly out of scope. If a phase needs parallelism, split it or invoke `/fan-out` at the outer layer.

### Preflight

- Accepts a path to a dev-plan file. If no arg, scan `docs/dev_plans/` for most-recent `.md` by mtime.
- Reads the plan and looks for a **review marker footer**, which MUST be the final non-empty line of the file, matching regex `^<!-- reviewed: \d{4}-\d{2}-\d{2} @ [0-9a-f]{40} -->\s*$`. Only the final line is checked; marker-shaped text anywhere else in the plan (e.g., inside prose or code fences documenting the format) is ignored. Written by `/review-plan` after the user accepts findings (Phase 1).
- `<plan-content-hash>` is `git hash-object <tmpfile>` where `<tmpfile>` is the plan with its final line removed if that final line matched the marker regex (otherwise the plan as-is). This makes hashing idempotent and deterministic.
- **Stale-marker check**: recompute the hash per the rule above and compare to the marker's recorded hash; mismatch → treat as unreviewed.
- **Pre-commit health check**: run the repo's pre-commit / lint in non-fix mode on the unchanged tree (`pre-commit run --all-files`, or fall back to `make lint`/`npm run lint`/`ruff check .` per repo idiom, or skip if none). If it already fails, hard-stop with `Tree has pre-existing lint/hook failures; fix them before running /conduct` — this prevents subagent fix-loops chasing issues they didn't introduce.
- If marker absent or stale: hard-stop with `Run: /review-plan <plan-path>` and exit.
- Load `<repo-root>/.conduct/state-<plan-basename>.json` if present. Support `--resume`, `--status`, `--abort-run`, `--pause-phase` (see Abort semantics).
- Parse phases from `## Implementation Checklist` using regex: `^###\s+Phase\s+(\S+)\s*:\s*(.+?)\s*(\([^)]*\))?\s*$` (captures phase label + title, handles colons in title tail, strips parenthesised annotations). Skip phases whose task checkboxes are all `- [x]`. Order by document position; record both the document position (0-based) and the Phase label verbatim.

### Per-phase workflow

For each unfinished phase:

1. **Parse phase contract** from the phase block. Expected slots (added to dev-plan template in Phase 5):
   - `Impl files:` — comma-separated list of likely implementation file paths (globs allowed)
   - `Test files:` — comma-separated list of likely test file paths (globs allowed)
   - ``Test command: `<cmd>` `` — single canonical test invocation for this phase
   - Any of these may be absent; conductor falls back as documented in §"Fallbacks" below.

2. **Parallel vs sequential decision.** If `Impl files:` and `Test files:` resolve to disjoint paths → parallel. If they overlap (same file, or one is a subpath of the other) → sequential (implementer first). If either slot is missing → default sequential. Log the decision in the phase summary.

3. **Spawn subagents** via `Agent` tool with `subagent_type: general-purpose`. Shared workspace. Each gets a filled prompt template — no parent conversation history is passed; this is the `Agent` tool's default behaviour (same pattern as `review-plan` and `deep-review`). Wall-clock timeouts are not enforceable by the conductor because the `Agent` tool invocation is synchronous within the parent turn (no PID to signal). This is a known v1 limitation; mitigated by the fix-loop cap + explicit iteration count in prompts. If misbehaving-long subagents become a real problem, a later iteration may move to a subprocess model like `fan-out.sh`.

4. **Await both.** Each subagent MUST emit a final fenced ` ```json ` block matching the schema below. If the report is malformed, the conductor hands back with a `schema_error` status in state — no retry. A clean-context respawn cannot meaningfully consume "your output didn't match schema" because the new subagent has no memory of the prior attempt. The user decides whether to re-run `/conduct --resume` or adjust the prompt.

5. **Run tests.** Resolve test command in this order:
   - `--test-cmd` CLI flag
   - Phase's `**Test command:**` line (parser regex: `^\*\*Test command:\*\*\s+\x60([^\x60]+)\x60\s*$`; first match in the phase block wins; additional matches emit a warning and are ignored; case-sensitive; backticks required)
   - Repo default from `package.json` scripts.test, `pyproject.toml` `[tool.pytest.ini_options]`, or `Makefile` `test` target
   - If none: warn, skip tests for this phase, flag in state and handback message.

   Test runner wall-clock is enforced via a shell `timeout` wrapper: default 5 min, override via `--test-timeout`. Enforcement is real because the test runner is a subprocess; this differs from the agent-timeout note above.

6. **Fix loop, bounded at N=3** (override `--max-iterations`). **No classifier.** On failure:
   - Pass full test-runner output + prior diff + iteration count to a respawned implementer.
   - Implementer's JSON report includes a flag `test_contract_mismatch: bool` with optional `explanation`.
   - If the respawned implementer sets `test_contract_mismatch: true`, conductor instead respawns the test-writer with the same failures on the next iteration.
   - Iteration count persists to state file after each attempt (crash recovery).
   - Pre-commit hook failures on the phase boundary commit (step 8) count as fix-loop iterations, routed to implementer with the hook output in place of test failures.
   - On cap reached: hand back with blocker message `Phase N stalled after 3 iterations; see .conduct/state-<plan>.json for diff and failure history.` Do not auto-advance.

7. **Optional mid-phase lightweight review.** Conductor MAY spawn a single reviewer subagent (never `/deep-review`) when diff > 200 lines, > 3 files touched, or phase tagged high-risk in Review Focus. One-shot, not looped. Reviewer's findings are logged but do not block phase completion.

8. **Commit at phase boundary.** After tests pass:
   - **Rogue-commit check.** Compare `git rev-parse HEAD` to `base_sha` from state (or phase-start SHA). If HEAD advanced, a subagent committed despite the prompt directive; conductor does NOT stack another commit — instead, annotate state with `rogue_commit_sha` and proceed to handback with a warning. This is a prompt-compliance signal, not a hard failure.
   - Otherwise: conductor runs `git commit -m "conduct: phase N — <phase title>"`. Commit author = current git user (no impersonation).
   - If the pre-commit hook fails, route to fix loop (step 6). Do NOT use `--no-verify`.
   - Record commit SHA in state file.

9. **Pause for handback.** Conductor:
   - Prints structured phase summary: files changed, tests passed, mid-review findings if any.
   - Prints literal next command the user can paste: `Run: /conduct --resume <plan-path>`.
   - Persists state (marked `awaiting_user` with last commit SHA).
   - Exits the skill. No keyword heuristic; user runs the printed command when ready.

### State file

`<repo-root>/.conduct/state-<plan-basename>.json`. Repo-root resolved via `git rev-parse --show-toplevel`. `.conduct/` added to `.gitignore`.

Schema:

```json
{
  "plan_path": "docs/dev_plans/...",
  "plan_content_hash": "<sha1 of plan with marker stripped>",
  "base_sha": "<git sha before phase 1>",
  "resume_base_sha": "<git sha at the start of this --resume invocation; absent on first run>",
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

**Lockfile**: conductor acquires an advisory lock on `.conduct/state-<plan-basename>.json.lock` before writing. Primary mechanism is a small Python helper (`.claude/skills/conduct/lock.py`) that uses `fcntl.flock` on the lockfile fd — portable across macOS and Linux without extra tooling. Fallback if Python is unavailable: atomic `mkdir` lockdir. Stale locks older than 1 h are broken with a warning. `flock(1)` is NOT used — it is not present by default on macOS. Two `/conduct` invocations on the same plan in the same worktree race on the same lock; across sibling worktrees each has its own state file (distinct `git rev-parse --show-toplevel`).

### Abort semantics

Naming is chosen so the more-destructive flag has the more-explicit name.

- `/conduct --pause-phase <plan>` → `git stash push -u -m "conduct-pause-phase-<N>"` to capture any uncommitted work, mark phase as "user-paused" in state (state lives; `--resume` can pick up), exit. User decides whether to drop or pop the stash. Does NOT run `git reset --hard` or `git clean`.
- `/conduct --abort-run <plan>` → discard state file entirely, no git operations, no stash. State dies; next `/conduct` starts fresh.
- Usage message prints both flags side-by-side with a one-line disambiguation.

### Subagent report schemas

All reports use two distinct phase identifiers:
- `phase_position`: 0-based index by document order (what conductor uses internally)
- `phase_label`: verbatim label from the `### Phase N:` heading (what humans read)

**Implementer** final ` ```json ` block:

```json
{
  "role": "implementer",
  "phase_position": 0,
  "phase_label": "1",
  "iteration": 0,
  "files_changed": ["src/foo.py", "src/bar.py"],
  "summary": "One-paragraph human-readable summary",
  "flags": {
    "blocked": false,
    "test_contract_mismatch": false,
    "explanation": null,
    "needs_test_coverage": []
  }
}
```

**Test-writer** final ` ```json ` block:

```json
{
  "role": "test-writer",
  "phase_position": 0,
  "phase_label": "1",
  "iteration": 0,
  "test_files_added": ["tests/test_foo.py"],
  "test_commands": ["pytest tests/test_foo.py -v"],
  "coverage_summary": "Covers acceptance criteria 1–3; gap on error path X",
  "flags": {
    "blocked": false,
    "needs_impl_clarification": null
  }
}
```

**Reviewer** final ` ```json ` block:

```json
{
  "role": "reviewer",
  "phase_position": 0,
  "phase_label": "1",
  "findings": [
    { "category": "Risk", "severity": "Important", "finding": "...", "suggestion": "..." }
  ]
}
```

### Fallbacks

- Missing `Impl files:` / `Test files:` → sequential spawn
- Missing `Test command:` → resolve from repo defaults, then `--test-cmd`, then skip with warning
- Missing Testing Notes entirely → same as above; phase completes on implementer success alone (flagged)

## Review Focus

- **Delegation depth invariant.** No subagent prompt template mentions `/deep-review`, `/fan-out`, `/review-plan`, or any skill that spawns agents. Verified by grep in Phase 6.
- **Context isolation.** Each subagent invocation passes a filled template as the full prompt; no parent conversation threading. Verified by Phase 6 sentinel test.
- **Fix-loop termination.** Hard N=3 cap with graceful handback.
- **Plan-readiness precondition.** Hard-stop on missing or stale marker (content-hash compare).
- **Shared-workspace safety.** Sequential fallback on declared file overlap. Commit-at-boundary only.
- **Self-host bootstrap.** Phase 6 includes explicit steps to acquire a real marker on this plan after Phase 1 ships.

## Implementation Checklist

### Phase 1: `/review-plan` writes the review marker

**Impl files:** `.claude/skills/review-plan/SKILL.md`
**Test files:** none (manual verification)
**Test command:** none (manual)

- [x] **Resolve contract conflict first.** `review-plan/SKILL.md:142,151` currently says "Do NOT modify the plan automatically" / "Never modify the plan file directly." Rewrite both lines to carve out the marker footer: "Never modify the plan *body* automatically; findings drive a conversation. The sole exception is the review marker footer — a single trailing comment line appended after the user explicitly accepts or waives findings."
- [x] After the findings-presentation step, add a prompt: "Are findings addressed (yes/waive/no)?"
- [x] On `yes` or `waive`: compute the plan hash per the rule in `/conduct` Preflight (strip only the final line if it matches the marker regex, then `git hash-object`), append or replace the final line with `<!-- reviewed: YYYY-MM-DD @ <hash> -->`.
- [x] On `no`: exit without writing.
- [x] Document marker format, hash-computation rule, and "final line only" semantics in `review-plan/SKILL.md`.
- [x] Phase 1 manual verification (this phase only): run `/review-plan` on a scratch plan, answer `yes`, confirm the marker line is appended as the final line and has the expected format. Edit the plan body (non-marker line), re-run `/review-plan`, answer `yes`, confirm marker is replaced (not duplicated) and hash updated. Stale-detection verification is deferred to Phase 6 because it requires `/conduct` preflight.

### Phase 2: `/dev-plan` template extension

**Impl files:** `.claude/skills/dev-plan/template.md`, `.claude/skills/dev-plan/SKILL.md`
**Test files:** none
**Test command:** none

- [x] Extend template Phase sections with three optional slots immediately under each `### Phase N:` heading: `**Impl files:**`, `**Test files:**`, ``**Test command:** `<cmd>` ``
- [x] Update `dev-plan/SKILL.md` to explain these slots and when to fill them (omit when trivially inferable; required for `/conduct`-driven phases)
- [x] Update this plan (20260422-feature-conduct-skill.md) to include the slots for its own phases (already done in this v3 draft — verify)

### Phase 3: Conduct skill scaffolding

**Impl files:** `.claude/skills/conduct/SKILL.md`, `.claude/skills/conduct/implementer-prompt.md`, `.claude/skills/conduct/test-writer-prompt.md`, `.claude/skills/conduct/reviewer-prompt.md`
**Test files:** none (templates are verified in Phase 6)
**Test command:** `grep -E '/(deep-review|fan-out|review-plan|conduct)' .claude/skills/conduct/*.md && echo FAIL || echo OK`

- [x] Create `.claude/skills/conduct/` directory
- [x] Write `SKILL.md` with frontmatter (name, description, trigger phrases: "step through plan", "walk phases", "delegate phase implementation", "conduct plan", "run the plan") and the workflow body from the Requirements section
- [x] Write `implementer-prompt.md` template with placeholders `{{PLAN_PATH}}`, `{{PHASE_INDEX}}`, `{{PHASE_TITLE}}`, `{{PRIOR_DIFF}}`, `{{TEST_FAILURES}}`, `{{ITERATION}}`, `{{BASE_SHA}}`. Includes: "do not invoke slash commands or skills"; "stage with `git add`, do not commit"; final JSON report schema
- [x] Write `test-writer-prompt.md` template with placeholders `{{PLAN_PATH}}`, `{{PHASE_INDEX}}`, `{{PHASE_TITLE}}`, `{{EXISTING_TESTS}}`, `{{BASE_SHA}}`. Same directives + test-writer JSON schema
- [x] Write `reviewer-prompt.md` template with placeholders `{{PLAN_PATH}}`, `{{PHASE_INDEX}}`, `{{DIFF}}`. One-shot, reviewer JSON schema
- [x] Verify: run the `grep` test command above to confirm no prompt references skill-spawning slash commands

### Phase 4: Conductor logic in SKILL.md

**Impl files:** `.claude/skills/conduct/SKILL.md`
**Test files:** none (manual verification)
**Test command:** none (Phase 6 exercises this)

- [x] Document preflight algorithm: plan path resolution, marker read + stale check (hash recompute), phase parsing regex, state-file load
- [x] Document per-phase workflow (steps 1–9 from Requirements) including the parallel-vs-sequential heuristic, subagent spawn, JSON report parse-or-retry-once, fix loop N=3, pre-commit-hook-as-iteration routing, boundary commit, handback message with literal `Run: /conduct --resume` line
- [x] Document pause/abort semantics (`--pause-phase` = stash; `--abort-run` = drop state)
- [x] Document timeouts and CLI flags (`--test-timeout`, `--max-iterations`, `--test-cmd`, `--resume`, `--status`, `--pause-phase`, `--abort-run`)

### Phase 5: State file + lockfile

**Impl files:** `.claude/skills/conduct/SKILL.md` (algorithm), `.claude/skills/conduct/parser.py`, `.claude/skills/conduct/marker.py`, `.claude/skills/conduct/lock.py`, `.claude/skills/conduct/tests/` (deterministic tests — see below), `.gitignore`
**Test files:** `.claude/skills/conduct/tests/test_parser.py`, `.claude/skills/conduct/tests/test_marker.py`, `.claude/skills/conduct/tests/test_state.py`, `.claude/skills/conduct/tests/test_skill_spawn_grep.sh`
**Test command:** `uvx pytest .claude/skills/conduct/tests/ -v && bash .claude/skills/conduct/tests/test_skill_spawn_grep.sh`

**Test deps**: pytest is invoked through `uvx` so no project-level install is required. Stock `python3 -m pytest` only works if the user has pytest installed system-wide; `uvx` is the documented invocation.

- [x] Document state file schema in `SKILL.md` exactly as specified in Requirements §"State file"
- [x] Document path resolution: `$(git rev-parse --show-toplevel)/.conduct/state-$(basename <plan>).json`
- [x] Write `lock.py` helper: `fcntl.flock` on lockfile fd; 1 h stale-break rule; atomic `mkdir` fallback if Python is unavailable
- [x] Add `.conduct/` to `.gitignore`
- [x] Write `tests/test_parser.py`: phase regex on synthetic headings (colons, parens, non-contiguous numbering, already-completed phases); `Test command:` regex (backticks, multiple matches, malformed)
- [x] Write `tests/test_marker.py`: hash-strip idempotency (marker in final line strips; marker-shaped lines in body do NOT strip); round-trip through append-or-replace
- [x] Write `tests/test_state.py`: state-file schema round-trip; lockfile acquisition/release; stale-lock break
- [x] Write `tests/test_skill_spawn_grep.sh`: greps `.claude/skills/conduct/*.md` for skill-spawn phrases (`/deep-review`, `/fan-out`, `/review-plan`) used as actions — exits non-zero on any match outside a designated allow-list (e.g., "do NOT invoke /deep-review" is allowed prose)

### Phase 6: Manual verification

**Impl files:** none (scratch plans under `/tmp/conduct-verify/`)
**Test files:** scratch test fixtures created per scenario
**Test command:** per scenario

- [ ] **Acquire real marker on this plan.** After Phase 1 ships, run `/review-plan docs/dev_plans/20260422-feature-conduct-skill.md`, accept findings, confirm marker footer appears.
- [x] **Happy path.** Covered by `tests/test_conductor_harness.py::test_happy_path_single_phase_commits_and_hands_back` and `::test_multi_phase_via_resume_advances_one_phase_at_a_time` — stub-spawner harness exercises both subagents passing first try, real `git commit` at boundary, and `--resume` advancing to the next phase.
- [x] **Assertion failure → implementer respawn.** Covered by `tests/test_conductor_harness.py::test_assertion_failure_respawns_implementer_and_passes_on_iteration_1`. Asserts the conductor reset the index, threaded prior_diff + test_failures into iteration 1, and recorded `iteration_count = 1`.
- [x] **Test contract mismatch → test-writer respawn.** Covered by `tests/test_conductor_harness.py::test_test_contract_mismatch_routes_iteration_1_to_test_writer`. Implementer iteration-0 report sets `test_contract_mismatch: true`; iteration-1 spawn is the test-writer, not the implementer.
- [x] **Fix-loop cap.** Covered by `tests/test_conductor_harness.py::test_fix_loop_cap_blocks_after_three_iterations`. Four implementer spawns (iterations 0–3) then `state.status = "blocked"` with the stalled-after-N message.
- [x] **Preflight hard stop.** Covered by `tests/test_preflight.py::test_preflight_rejects_unmarked_plan` — `marker_is_stale` returns the no-marker sentinel, which the conductor maps to the "Run: /review-plan ..." hard stop.
- [x] **Preflight stale marker.** Covered by `tests/test_preflight.py::test_preflight_detects_stale_marker` and `::test_preflight_any_body_change_invalidates_marker[*]`.
- [x] **Marker-in-body safety.** Covered by `tests/test_preflight.py::test_preflight_marker_in_body_does_not_falsely_validate` and `::test_preflight_marker_after_in_body_examples_is_the_one_that_counts`.
- [x] **Pre-existing lint failure.** Covered by `tests/test_conductor_harness.py::test_preflight_lint_failure_hard_stops_before_any_spawn`. Stub `lint_check` returns a diagnostic; conductor returns `status="preflight_fail"` and never invokes the spawn or test-runner seams.
- [x] **Context isolation.** Covered by `tests/test_conductor_harness.py::test_context_isolation_no_sentinel_leaks_into_rendered_prompts`. Sentinel set in the parent process env / test scope; rendered prompts (which include every templated placeholder) contain zero hits.
- [x] **File-overlap sequential fallback.** Demonstrated by `tests/test_parser.py::test_files_overlap_*` plus the integration check in `tests/test_preflight.py::test_preflight_parses_phases_with_completion_and_glob_slots`. Conductor's branch on the result is straight-line text in SKILL.md Step 2.
- [x] **Missing test command.** Covered by `tests/test_conductor_harness.py::test_missing_test_command_warns_and_completes_phase`. No `Test command:` slot, no override; conductor records the skip warning, never calls the test runner, and still commits the phase.
- [x] **Pre-commit hook failure routed to fix loop.** Covered by `tests/test_conductor_harness.py::test_precommit_hook_failure_routes_to_fix_loop`. Real `.git/hooks/pre-commit` fails attempt 1 and passes attempt 2; conductor counts the failure as `iteration_count = 1`, threads hook output into the next implementer spawn as `test_failures`, and lands the boundary commit on attempt 2.
- [x] **Resume across process restart.** Covered by `tests/test_conductor_harness.py::test_resume_across_simulated_restart_picks_up_at_next_phase`. Phase 1 completes; the in-memory state object is discarded; a brand-new `ConductOptions` with `resume=True` reads only the on-disk state file and advances to phase 2.
- [x] **Pause phase.** Covered by `tests/test_conductor_harness.py::test_pause_phase_stashes_and_marks_state`. `pause_phase` runs `git stash push -u -m conduct-pause-phase-<title>`, sets `state.status = "paused"`, exits without touching `git reset`.
- [x] **Abort run.** Covered by `tests/test_conductor_harness.py::test_abort_run_deletes_state_without_touching_tree`. State file deleted; user's working tree files (incl. uncommitted `scratch.txt`) preserved; no stash created.
- [x] **Rogue-commit detection.** Covered by `tests/test_conductor_harness.py::test_rogue_commit_detection_does_not_stack_a_second_commit`. Stub implementer runs `git commit` mid-spawn; conductor detects HEAD ≠ baseline at Step 8, records `rogue_commit_sha`, sets `commit_sha = None`, and refuses to stack a second commit.
- [x] **Schema error hard-stop.** Covered by `tests/test_schema.py::test_extract_raises_when_no_block`, `::test_parse_report_invalid_json_raises`, and the missing-key / wrong-type / role-mismatch cases. `parse_report` raises `SchemaError`; SKILL.md Step 4 maps every `SchemaError` to `state.status = "schema_error"` + handback (no respawn).
- [ ] **Self-host.** Run `/conduct docs/dev_plans/20260422-feature-conduct-skill.md` on itself (after marker acquired in step 1 above). Pure dogfood. Expected to need the usual handbacks but succeed end-to-end.
- [x] **Test-runner timeout.** Covered by `tests/test_runner.py::test_run_tests_timeout_kills_long_command` (sleep 10 with a 0.5s timeout — process killed promptly, `timed_out=True`, returncode `-1`, conductor routes that as a fix-loop failure per SKILL.md Step 6).
- [x] **Phase parsing.** Covered by `tests/test_preflight.py::test_preflight_parses_phases_with_completion_and_glob_slots` (end-to-end on a synthetic plan with annotation, completion, and glob slots) plus the unit-level coverage in `tests/test_parser.py`.

### Phase 7: Docs and integration

**Impl files:** `AGENTS.md`, `.claude/skills/dev-plan/SKILL.md`, `.claude/skills/review-plan/SKILL.md`, `.claude/skills/fan-out/SKILL.md`
**Test files:** none
**Test command:** none

Phase 7 MUST land before PR regardless of Phase 6 iteration count. Docs and code ship together.

- [x] `AGENTS.md`: add `/conduct` to skill index; reword the depth-invariant paragraph to preserve existing vocabulary: "Workers launched in a fresh Claude subprocess (e.g., via `fan-out.sh spawn`) start a new orchestrator/worker tree and may themselves act as orchestrators; the one-level rule applies per-tree."
- [x] `.claude/skills/dev-plan/SKILL.md`: add pointer to `/conduct` as the "execute a reviewed plan" companion; mention the per-phase `Impl files:` / `Test files:` / `Test command:` slots
- [x] `.claude/skills/review-plan/SKILL.md`: document the marker footer it writes and that `/conduct` consumes it
- [x] `.claude/skills/fan-out/SKILL.md`: note that a fan-out-spawned subprocess may invoke `/conduct` as its top-level skill; `/conduct` itself does not fan out
- [x] Do NOT touch `.codex/skills/`

## Technical Specifications

### Files to Modify

- `.claude/skills/review-plan/SKILL.md` — Phase 1
- `.claude/skills/dev-plan/template.md` — Phase 2
- `.claude/skills/dev-plan/SKILL.md` — Phases 2 & 7
- `.claude/skills/fan-out/SKILL.md` — Phase 7
- `AGENTS.md` — Phase 7
- `.gitignore` — Phase 5 (add `.conduct/`)

### New Files to Create

- `.claude/skills/conduct/SKILL.md`
- `.claude/skills/conduct/implementer-prompt.md`
- `.claude/skills/conduct/test-writer-prompt.md`
- `.claude/skills/conduct/reviewer-prompt.md`
- `.claude/skills/conduct/lock.py` — `fcntl.flock` helper with mkdir fallback
- `.claude/skills/conduct/tests/test_parser.py`
- `.claude/skills/conduct/tests/test_marker.py`
- `.claude/skills/conduct/tests/test_state.py`
- `.claude/skills/conduct/tests/test_skill_spawn_grep.sh`

### Architecture Decisions

- **Delegation depth = 1 per orchestrator tree.** Fan-out's subprocess model (`claude -p` in a worktree, per `fan-out.sh`) starts a new tree, so `fan-out → conduct` is valid. AGENTS.md reworded to use the per-tree framing.
- **Shared workspace, no worktrees.** Worktree isolation is the user's choice at the outer layer. Clean context is provided by the `Agent` tool's default (no parent conversation history), not by filesystem separation.
- **No fix-loop classifier.** Always respawn implementer with full runner output; implementer flags `test_contract_mismatch` in JSON report → conductor respawns test-writer next iteration.
- **JSON schema for subagent reports.** Fenced ` ```json ` at end of output. Single attempt — malformed report = hard `schema_error` status + handback, no retry (a clean-context respawn cannot consume a "your last output was bad" preamble).
- **Commit per phase** at the boundary by the conductor. Subagents stage only. Rogue commits by subagents are detected (not corrected) via HEAD-comparison. Pre-commit-hook failure on the boundary commit = fix-loop iteration.
- **Review marker** = `<!-- reviewed: YYYY-MM-DD @ <hash> -->` as the final line only; hash = `git hash-object` of plan with final marker line stripped (idempotent on re-review).
- **`/review-plan` owns a carve-out** in its no-modify contract: plan body stays immutable, marker footer is the single exception.
- **State file** at `<repo-root>/.conduct/state-<plan-basename>.json` with Python `fcntl.flock` lockfile (NOT `flock(1)` — unavailable on macOS by default).
- **Pre-commit health check at preflight** so fix-loops don't chase pre-existing lint failures.
- **No agent-timeout enforcement in v1.** The `Agent` tool gives no PID; test-timeout uses subprocess `timeout` wrapping and is real.
- **No keyword handback.** Exit message prints the literal `/conduct --resume <plan>` command; user copies and runs.
- **Abort naming.** `--pause-phase` = stash + keep state (recoverable). `--abort-run` = drop state (destructive). More-destructive flag has the more-explicit name. Neither uses `git reset --hard` or `git clean`.

### Dependencies

- `Agent` tool (clean-context default behaviour — matches `review-plan` / `deep-review` convention). Note: the `Agent` tool provides no PID or timeout lever; agent wall-clock enforcement is therefore a v1 known limitation.
- `git` (hash-object, stash, commit, rev-parse)
- `python3` (for `lock.py` — ships with macOS and most Linuxes by default; if absent, atomic `mkdir` lockdir fallback)
- `timeout` (GNU coreutils; on macOS install via `brew install coreutils` gives `gtimeout` — skill detects which is available) — only needed for `--test-timeout` enforcement
- Phase 1 (`/review-plan` marker) — blocking prerequisite for `/conduct` to be usable

### Integration Seams

| Seam | Writer | Caller | Contract |
|------|--------|--------|----------|
| Plan parsing | `/dev-plan` | `/conduct` | Plan contains `## Implementation Checklist` with `### Phase N: <title>` headings; optional per-phase `**Impl files:**`, `**Test files:**`, ``**Test command:** `<cmd>` `` slots |
| Review marker | `/review-plan` | `/conduct` | Trailing `<!-- reviewed: YYYY-MM-DD @ <hash> -->` footer written after user acceptance; hash = `git hash-object` of plan with marker stripped |
| Implementer contract | `/conduct` | implementer subagent | Filled template as full prompt; final ` ```json ` block with role, files_changed, summary, flags.{blocked, test_contract_mismatch, explanation, needs_test_coverage} |
| Test-writer contract | `/conduct` | test-writer subagent | Filled template as full prompt; final ` ```json ` block with role, test_files_added, test_commands, coverage_summary, flags.{blocked, needs_impl_clarification} |
| Reviewer contract (opt.) | `/conduct` | reviewer subagent | Filled template; final ` ```json ` block with findings list |
| State persistence | `/conduct` | itself (resume) | `<repo-root>/.conduct/state-<plan-basename>.json`, schema in Requirements §"State file"; `flock` lockfile |
| Handback | `/conduct` | user | Structured summary + literal `Run: /conduct --resume <plan>` line; skill exits |
| Fan-out subprocess | `/fan-out` | `/conduct` | Fan-out may spawn a Claude subprocess whose top-level skill is `/conduct`; subprocess boundary re-baselines depth |

## Testing Notes

### Test Approach

- Manual verification matrix in Phase 6 covers 16 scenarios spanning happy path, fix-loop branches, preflight, concurrency, abort, and self-host.
- Each scenario uses a scratch plan under `/tmp/conduct-verify/` (not committed) to avoid polluting `docs/dev_plans/`.
- Context-isolation test uses a sentinel string and prompt-capture logging; if the `Agent` tool does not expose prompt logging, add a temporary `echo "$PROMPT" > /tmp/captured-$(date +%s)` step in the spawn helper, remove after verification.

### Edge Cases Tested

Listed in Phase 6 as individual bullets — each edge case has its own checkbox.

## Issues & Solutions

### Issue 1: Self-hosting bootstrap
- **Problem**: `/conduct` hard-stops without a marker; this plan has none because Phase 1 ships the marker-writer. Chicken-and-egg.
- **Solution**: Phase 6's first verification step is explicitly "acquire a real marker on this plan by running `/review-plan` (after Phase 1 is merged locally) and accept findings." No hand-annotated markers.
- **Files affected**: `docs/dev_plans/20260422-feature-conduct-skill.md` (gets marker appended), Phase 6 checklist

### Issue 2: Fix-loop classifier heterogeneity across test runners
- **Problem**: pytest/jest/mocha/go test format parse errors, assertions, and fixture failures differently. A regex classifier in the conductor would misroute.
- **Solution**: Drop the classifier. Conductor always respawns implementer with the full runner output. Implementer's JSON report flag `test_contract_mismatch: true` re-routes the next iteration to test-writer. The subagent has runner context, the classifier didn't.
- **Files affected**: `.claude/skills/conduct/SKILL.md`, `.claude/skills/conduct/implementer-prompt.md`

### Issue 3: File-overlap heuristic unrealisable without data
- **Problem**: Conductor can't predict which files a phase touches without reading the subagent's mind.
- **Solution**: Require the plan author to declare `Impl files:` and `Test files:` slots per phase. Conductor compares declared paths, not predicts. Missing slots → sequential fallback (safe default).
- **Files affected**: `.claude/skills/dev-plan/template.md`, `.claude/skills/conduct/SKILL.md`

### Issue 4: Test-command extraction from free-form prose
- **Problem**: Testing Notes is unstructured.
- **Solution**: Canonical ``**Test command:** `<cmd>` `` slot per phase. Fallback chain: phase slot → `--test-cmd` → repo defaults → skip-with-warning.
- **Files affected**: `.claude/skills/dev-plan/template.md`, `.claude/skills/conduct/SKILL.md`

### Issue 5: Handback relies on main Claude behaviour not in scope
- **Problem**: No mechanism binds "proceed" to `/conduct --resume`. The skill has exited.
- **Solution**: Exit message prints the literal command. User copies and runs. No keyword heuristic.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 6: Stale marker after plan edit
- **Problem**: A marker dated YYYY-MM-DD survives arbitrary post-review edits.
- **Solution**: Marker records `git hash-object <plan>` computed with marker line stripped. Preflight recomputes; mismatch = stale = hard stop.
- **Files affected**: `.claude/skills/review-plan/SKILL.md`, `.claude/skills/conduct/SKILL.md`

### Issue 7: Free-form subagent reports
- **Problem**: Conductor can't parse prose reliably for flags, file lists, etc.
- **Solution**: Final ` ```json ` block with pinned schema per role. Parse-or-retry-once, then hard error. Schema documented in this plan and enforced in prompts.
- **Files affected**: `.claude/skills/conduct/*-prompt.md`, `SKILL.md`

### Issue 8: Pre-commit hook failure = lost work
- **Problem**: Conductor commits at phase boundary; if a hook fails, what now?
- **Solution**: Hook output replaces "test failures" in the fix-loop input; counts as one iteration; routed to implementer (who owns code quality). No `--no-verify`.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 9: Abort semantics hit the destructive-command deny list
- **Problem**: `git reset --hard` and `git clean` are denied in permissions.
- **Solution**: `--pause-phase` uses `git stash push -u -m "conduct-pause-phase-<N>"`; state lives so `--resume` picks up. `--abort-run` drops state without stashing. User decides to drop any stash.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 10: Missing timeouts leave conductor hung
- **Problem**: Subagent or test-runner hang → conductor waits forever.
- **Solution**: Test-runner wall-clock enforced via subprocess `timeout` wrapper (`--test-timeout 5m` default). Agent-timeout is NOT enforceable — the `Agent` tool gives no PID; documented as a v1 known limitation. Mitigated by fix-loop cap.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 11: `/review-plan` immutability contract conflicts with marker-writing
- **Problem**: `review-plan/SKILL.md:142,151` explicitly forbids modifying the plan file. Phase 1 adds marker-writing.
- **Solution**: Phase 1 rewrites both constraint lines to carve out the marker footer as the single exception: plan body immutable, trailing comment marker allowed after explicit user acceptance.
- **Files affected**: `.claude/skills/review-plan/SKILL.md`

### Issue 12: `flock(1)` unavailable on macOS by default
- **Problem**: `which flock` fails on default macOS; plan originally claimed "present on Linux and macOS/homebrew" — wrong.
- **Solution**: Python `fcntl.flock` helper (`lock.py`) with atomic `mkdir` lockdir fallback. Python 3 ships with macOS. No dependency on `flock(1)`.
- **Files affected**: `.claude/skills/conduct/lock.py`, `.claude/skills/conduct/SKILL.md`

### Issue 13: Hash-strip regex collides with marker-shaped text in plan body
- **Problem**: Plans may legitimately contain marker-shaped strings in prose or code fences (this plan does). A naive `grep -v` strips all of them before hashing, breaking the self-host test.
- **Solution**: Strip ONLY the final line if it matches the strict regex `^<!-- reviewed: \d{4}-\d{2}-\d{2} @ [0-9a-f]{40} -->\s*$`. Body untouched. Verified by Phase 6 marker-in-body scenario + `tests/test_marker.py`.
- **Files affected**: `.claude/skills/review-plan/SKILL.md`, `.claude/skills/conduct/SKILL.md`, `.claude/skills/conduct/tests/test_marker.py`

### Issue 14: Parse-or-retry-once is meaningless with clean-context subagents
- **Problem**: A fresh subagent respawned with "your output didn't match the schema" prepended has no memory of its prior attempt — the retry is just a duplicate attempt.
- **Solution**: Drop the retry. Malformed JSON → `schema_error` state + handback. User inspects and re-invokes.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 15: Subagents can commit despite prompt directive
- **Problem**: "Stage only" is prompt-level only; nothing prevents a subagent from running `git commit`.
- **Solution**: Conductor compares `HEAD` to `base_sha`/phase-start SHA before its own boundary commit. If HEAD advanced, record `rogue_commit_sha` in state and handback with a warning rather than stacking another commit.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 16: Pre-existing lint failures trigger pointless fix-loops
- **Problem**: Conductor's boundary commit runs pre-commit hooks. If the repo already has lint issues unrelated to the phase's work, phase 1's commit fails and the implementer is asked to fix things it never touched.
- **Solution**: Preflight runs `pre-commit run --all-files` (or repo-idiomatic equivalent) once; hard-stops with a clear diagnostic if the tree is already dirty. Fix-loops only chase issues the subagents actually introduced.
- **Files affected**: `.claude/skills/conduct/SKILL.md`

### Issue 17: Phase 1 verification circular dependency
- **Problem**: Phase 1 verification originally required `/conduct` preflight (stale-detection test) — but `/conduct` doesn't exist until Phase 4.
- **Solution**: Split verification. Phase 1 verifies only "marker appears + idempotent replace." Stale-detection moves to Phase 6 where `/conduct` is available.
- **Files affected**: Phase 1 checklist, Phase 6 checklist

## Acceptance Criteria

- [ ] `/conduct <plan-path>` runs a 2-phase scratch plan end-to-end without intervention on the happy path
- [ ] Conductor pauses between phases with a handback message that prints the literal `Run: /conduct --resume <plan>` line
- [ ] Fix loop respawns implementer by default; respawns test-writer on the next iteration when implementer flags `test_contract_mismatch: true`; terminates at N=3 with blocker message
- [x] Preflight hard-stops when plan lacks marker OR marker hash mismatches current content (with final-line-only strip semantics); covered by `tests/test_preflight.py`. Pre-existing lint/hook portion still relies on conductor wiring at runtime (SKILL.md Preflight §3).
- [ ] Pre-commit-hook failures at phase boundary count as fix-loop iterations, not hard errors
- [x] Malformed subagent JSON → `schema_error` status + handback; no silent retry. `schema.parse_report` raises `SchemaError` for missing blocks, parse failures, role mismatch, missing keys, wrong types; `tests/test_schema.py` covers all paths.
- [ ] Rogue commits by subagents are detected via HEAD comparison and flagged in state; conductor does not stack a second commit
- [ ] All subagent prompts are filled templates; no inline prose in the body of `SKILL.md` other than workflow text
- [ ] `/review-plan` writes the marker after user acceptance; `review-plan/SKILL.md` constraint lines updated to reflect the footer carve-out; Phase 1 shipped independently before Phase 6 self-host
- [ ] `<repo-root>/.conduct/state-<plan-basename>.json` supports `--resume`, `--status`, `--pause-phase`, `--abort-run` with Python `fcntl.flock` locking (no dependency on `flock(1)`)
- [ ] Commit per phase with message `conduct: phase N — <title>`; author = current git user
- [x] `--test-timeout` proven by `tests/test_runner.py` (Python-native subprocess timeout, no coreutils dep). `--max-iterations` and `--test-cmd` are conductor-side wiring still pending end-to-end demonstration. (agent-timeout deferred to post-v1.)
- [ ] `--pause-phase` uses `git stash -u`; `--abort-run` only touches state; no `reset --hard` prompts surface
- [ ] Docs updated in `AGENTS.md`, `dev-plan/SKILL.md`, `review-plan/SKILL.md`, `fan-out/SKILL.md`; no edits to `.codex/skills/`; Phase 7 lands before PR regardless of Phase 6 iteration count
- [x] Automated tests under `.claude/skills/conduct/tests/` pass: parser, marker-hash, state, skill-spawn-grep, schema, runner, preflight (53 passing).
- [ ] Sentinel test confirms no parent-conversation text leaks into subagent prompts
- [ ] Code reviewed and approved (regular review + `/deep-review`)
- [ ] All Phase 6 manual scenarios pass (including rogue-commit, schema-error, marker-in-body safety, pre-existing lint failure)
- [ ] Documentation updated

## Final Results

_Fill when complete._

### Summary

### Outcomes

### Learnings

### Follow-up Work

- **Skill namespacing** (`workflow:dev-plan`, `workflow:conduct`, …) — evaluate after conduct proves the workflow.
- **Codex parity** — user to assess separately.
- **LLM-based fix-loop classifier** — current design leans on the implementer's self-reported flag. If misrouting is common in practice, consider a tiny classifier call.
<!-- reviewed: 2026-04-22 @ 54b56d3e251447fa1deda3979177bd9d60098a4c -->
