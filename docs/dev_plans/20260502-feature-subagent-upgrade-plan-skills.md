# Task: Subagent upgrades for dev-plan and review-plan skills

**Status**: Not Started
**Assigned to**: Claude Code
**Priority**: Medium
**Branch**: feature/subagent-upgrade-plan-skills
**Created**: 2026-05-02
**Completed**:

## Objective

Add subagent-driven exploration to `dev-plan create` and parallel multi-lens review to `review-plan`, so plans are grounded in verified codebase facts and audits surface what a single-pass reviewer misses.

## Context

`dev-plan` currently relies on whatever the main agent already knows about the repo when drafting "Files to Modify" and "Technical Specifications". This produces plans that reference paths or APIs the main agent never verified — a failure mode `review-plan` catches *after* the fact.

`review-plan` already spawns one isolated-context subagent. It works, but it conflates several review lenses (architecture, sequencing, spec, codebase claims) into a single prompt. The deep-review skill demonstrates that splitting lenses across parallel subagents produces deeper, more specific findings without bloating any one context.

Both skills are mirrored to `.codex/skills/` and promoted to `~/.claude/` and `~/.codex/` via `just promote-skills`. Any change has to land in both mirrors with parity.

**Harness ownership:** Claude Code edits the `.claude/skills/<skill>/SKILL.md` files; Codex CLI edits the `.codex/skills/<skill>/SKILL.md` files. Each harness is responsible for its own mirror so harness-specific phrasing (subagent spawn idiom, tool names) stays idiomatic in each. `just check-sync` is the parity gate after both sides have updated.

## Requirements

- `dev-plan create` spawns one Explore subagent during the drafting pass to gather codebase facts: which referenced files exist, prevailing patterns in target areas, dependency versions from `package.json` / `pyproject.toml` / `Cargo.toml`. Findings inform Technical Specifications and Files-to-Modify before the plan file is written.
- `dev-plan update` and `dev-plan complete` are unchanged — exploration cost is only paid on `create`.
- `review-plan` runs four parallel lens subagents instead of one monolithic reviewer:
  - `architecture` — patterns, coupling, integration seams
  - `sequencing` — task order, hidden dependencies, missing migrations/config
  - `spec-and-testing` — Review Focus, RFC/spec references, test coverage gaps
  - `codebase-claims` — verify every file/API/dependency the plan references actually exists
- Each lens runs in isolated context (no parent conversation) at `opus`, returns structured findings (Category / Severity / Finding / Evidence / Suggestion), and the orchestrator merges them by severity for the user.
- Review marker logic (hash-above-marker, idempotent rewrite, placeholder validation) is unchanged.
- `.claude/` and `.codex/` skill files stay in lockstep — same dispatch, same lens names, same finding schema. `just check-sync` passes.
- Backward compatibility: existing `/review-plan [path]` invocation works the same way at the user-visible level. Nothing in the plan-file format changes.

## Review Focus

- **Mirror parity** — `.claude/skills/dev-plan/SKILL.md` and `.codex/skills/dev-plan/SKILL.md` (and same for review-plan) describe the same subagent dispatch, same lens definitions, same prompt templates. `just check-sync` is the gate.
- **Single-level delegation** — the existing review-plan rule ("reviewer does not spawn further subagents") applies per-lens too. Each lens is a leaf agent. The skill is the orchestrator. No nested fan-out.
- **Context isolation** — every spawned subagent receives only its lens prompt + plan content + codebase access. No parent conversation history leaks in. Verify the spawn templates make this explicit.
- **Cost discipline** — four `opus` subagents per `/review-plan` is a real token cost. Document this in the skill so users understand the trade-off; don't silently 4x the bill.
- **dev-plan exploration scope** — the Explore subagent must produce structured facts the main agent then weaves into the plan. It must NOT draft plan prose itself; the main agent owns the plan body.

## Implementation Checklist

### Phase 1: review-plan parallel lenses (.claude side)

**Impl files:** `.claude/skills/review-plan/SKILL.md`
**Test files:** N/A (skill is prose; no executable tests)
**Test command:** `just check-sync`
**Validation cmd:** `just lint-scripts`

- Replace single-subagent dispatch with four parallel lens spawns
- Define each lens prompt template (architecture, sequencing, spec-and-testing, codebase-claims)
- Specify finding schema and merge-by-severity logic in the orchestrator section
- Update "Why This Exists" and "Delegation Pattern" to reflect parallelism
- Preserve review-marker logic verbatim
- Add a "Cost" note documenting the 4x opus call

### Phase 2: review-plan .codex mirror

**Impl files:** `.codex/skills/review-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`

- Mirror Phase 1 changes into the codex skill
- Adjust harness-specific phrasing only (e.g., subagent spawn idiom) — keep lens definitions and finding schema identical

### Phase 3: dev-plan Explore subagent (.claude side)

**Impl files:** `.claude/skills/dev-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`

- Add a step to the `create` workflow: spawn one Explore subagent before drafting Technical Specifications and Files-to-Modify
- Define the Explore prompt: list referenced paths, scan for prevailing patterns in the target area, read manifest files for dependency versions, return structured facts only
- Document that exploration runs only on `create` (not `update` / `complete`)
- Make explicit that the main agent owns plan prose; Explore returns facts

### Phase 4: dev-plan .codex mirror

**Impl files:** `.codex/skills/dev-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`

- Mirror Phase 3 changes
- Preserve harness-specific phrasing for the Explore-equivalent spawn

### Phase 5: docs and promotion

**Impl files:** `README.md`, `AGENTS.md`
**Test files:** N/A
**Test command:** `just check-sync && just lint-scripts`

- Update skill descriptions in README.md / AGENTS.md if they describe internal mechanics
- Run `/update-docs` to catch any other stale references
- Final `just check-sync` to confirm mirror parity

## Technical Specifications

### Files to Modify
- `.claude/skills/review-plan/SKILL.md` — add parallel lens dispatch
- `.codex/skills/review-plan/SKILL.md` — mirror
- `.claude/skills/dev-plan/SKILL.md` — add Explore step in `create` workflow
- `.codex/skills/dev-plan/SKILL.md` — mirror
- `README.md`, `AGENTS.md` — only if their descriptions of these skills go stale

### New Files to Create
- None. All changes are edits to existing SKILL.md files.

### Architecture Decisions
- **Four lenses, not three or five** — matches deep-review's lens cardinality, gives each lens a distinct scope without overlap. `codebase-claims` is the cheap factual lens; the other three are judgment-heavy.
- **Lens prompts live inline in SKILL.md** — same pattern deep-review uses. No separate template files; keeps the skill self-contained for the promotion script.
- **dev-plan stays single-subagent** — exploration is fact-gathering, not adversarial review. Parallelism would just split a unified scan into fragments.
- **Opus for all subagents** — review quality justifies cost; dev-plan exploration also benefits from extended thinking when reasoning about which patterns are prevalent.

### Dependencies
- None new. Skills already use the Agent tool for subagent spawning.

### Integration Seams

| Seam | Writer (task) | Caller (task) | Contract |
|------|---------------|---------------|----------|
| Lens finding schema | review-plan lens prompt | review-plan orchestrator merge | Each lens returns `{category, severity, finding, evidence, suggestion}` items; severity ∈ {Critical, Important, Minor} |
| Explore facts | dev-plan Explore subagent | dev-plan main agent | Returns structured facts (verified paths, observed patterns, dependency versions); no prose, no plan drafting |
| Mirror parity | .claude SKILL.md edits | .codex SKILL.md edits | Same dispatch, same lens names, same prompt structure; only harness-specific phrasing differs |

## Testing Notes

### Test Approach
- [ ] `just check-sync` passes after every phase
- [ ] `just lint-scripts` passes
- [ ] Manual: run `/review-plan` against this very plan once Phase 1 lands (dogfooding)
- [ ] Manual: run `/dev-plan create feature dummy-test` to exercise the new Explore step (delete the dummy plan after)

### Test Results
- [ ] All existing checks pass
- [ ] New skills behave as documented in manual runs

### Edge Cases Tested
- [ ] One lens returns empty findings — orchestrator handles cleanly
- [ ] All lenses return empty — clean review summary, no manufactured findings
- [ ] Plan references files that don't exist — codebase-claims lens flags them as Critical
- [ ] Explore finds no manifest files — dev-plan still drafts a plan, just without dependency-version facts

## Acceptance Criteria

- `/review-plan` spawns four parallel lens subagents with isolated context and merges findings by severity
- `/dev-plan create` spawns one Explore subagent before drafting and uses its facts in Technical Specifications / Files-to-Modify
- `.claude/` and `.codex/` mirrors are in lockstep (`just check-sync` clean)
- Review-marker write/validate logic unchanged and still idempotent
- Skill descriptions in README.md / AGENTS.md remain accurate
- Code reviewed (`/review`, `/security-review`, `/deep-review`) and approved before merge

<!-- reviewed: YYYY-MM-DD @ <hash> -->
<!-- /review-plan writes the marker line above. Everything below is the workspace: edits here do NOT invalidate the marker. -->

## Progress

- [ ] Phase 1: review-plan parallel lenses (.claude side)
- [ ] Phase 2: review-plan .codex mirror
- [ ] Phase 3: dev-plan Explore subagent (.claude side)
- [ ] Phase 4: dev-plan .codex mirror
- [ ] Phase 5: docs and promotion

## Findings

- (append findings here as work proceeds)

## Issues & Solutions

(none yet)

## Final Results

(fill on completion)
