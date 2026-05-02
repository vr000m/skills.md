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

## Scope tags

Each requirement, phase, and decision below is tagged:

- **[GENERIC]** — applies to both harnesses; the contract is identical in `.claude/` and `.codex/`.
- **[CLAUDE]** — Claude Code only. Owned by Claude.
- **[CODEX]** — Codex CLI only. Owned by Codex (Codex maintainer reviews these parts independently).

The split exists because the two harnesses have different delegation primitives: Claude has the Agent tool with isolated-context spawning; Codex has conditional `spawn_agent` with an in-session sequential fallback already codified in `.codex/skills/deep-review/SKILL.md`. The lens *contract* (names, prompts, finding schema, rubric) is generic; the *dispatch mechanism* is harness-specific.

## Requirements

### Generic (both harnesses)

- **[GENERIC]** `review-plan` exposes four review lenses with these exact names and scopes:
  - `architecture` — patterns, coupling, integration seams
  - `sequencing` — task order, hidden dependencies, missing migrations/config
  - `spec-and-testing` — Review Focus, RFC/spec references, test coverage gaps
  - `codebase-claims` — verify every file/API/dependency the plan references actually exists
- **[GENERIC]** Each lens uses an identical prompt template across harnesses. Each prompt opens with an explicit "You have NOT been part of the conversation that produced this plan" clause (same wording as the existing single-subagent template).
- **[GENERIC]** Each lens returns structured findings: `{category, severity, finding, evidence, suggestion}` where `category ∈ {Assumption, Constraint, Ambiguity, Risk, Sequencing, Missing Task, Testing Gap}` and `severity ∈ {Critical, Important, Minor}`.
- **[GENERIC]** Orchestrator merges lens outputs by severity (Critical → Important → Minor) and presents a single combined report. Empty lenses are dropped silently; all-empty produces a clean review.
- **[GENERIC]** Both skills get a `rubric.md` mirroring the deep-review pattern: gradeable criteria the orchestrator self-checks before presenting findings (no manufactured findings, evidence is concrete, severity discipline). One rubric per skill (review-plan and dev-plan), mirrored in `.claude/` and `.codex/`.
- **[GENERIC]** Model assignment per role (cost-aware, not all opus):
  - `architecture`, `sequencing`, `spec-and-testing` lenses → `opus` (judgment-heavy)
  - `codebase-claims` lens → `haiku` (factual lookup, no extended reasoning required)
  - `dev-plan` Explore subagent → `sonnet` (light pattern reasoning over fact-gathering)
- **[GENERIC]** `dev-plan create` runs one Explore step that gathers codebase facts (which referenced paths exist, prevailing patterns in target areas, dependency versions from `package.json` / `pyproject.toml` / `Cargo.toml`) and feeds them into the Technical Specifications / Files-to-Modify sections **above the review marker**, at create time only. `dev-plan update` and `dev-plan complete` do not re-explore.
- **[GENERIC]** Explore returns structured facts only: verified paths, observed patterns, dependency versions. It does not draft plan prose; the main agent owns the plan body.
- **[GENERIC]** Review marker logic (hash-above-marker, idempotent rewrite, placeholder validation) is unchanged.
- **[GENERIC]** Mirror parity gate: `just check-sync` passes after both sides have updated. Lens names, prompt bodies, finding schema, and rubric content are byte-identical between `.claude/` and `.codex/`. Only the dispatch section diverges.
- **[GENERIC]** Backward compatibility: `/review-plan [path]` invocation is unchanged at the user-visible level. Plan-file format unchanged.

### Claude-specific

- **[CLAUDE]** review-plan dispatches the four lenses as parallel `Agent` calls with isolated context (no parent conversation history). Each call sets `model` per the table above.
- **[CLAUDE]** dev-plan Explore is a single `Agent` call with isolated context, model `sonnet`.

### Codex-specific

- **[CODEX]** review-plan dispatches the four lenses via `spawn_agent` when available, otherwise falls back to running them sequentially in-session — same pattern as `.codex/skills/deep-review/SKILL.md`. The fallback uses identical lens prompts and finding schema; only the spawn mechanism changes.
- **[CODEX]** dev-plan Explore follows the same convention: `spawn_agent` if available, otherwise inline fact-gathering with the same prompt and structured output contract.

## Review Focus

- **[GENERIC] Mirror parity** — lens names, prompt bodies, finding schema, and `rubric.md` content are byte-identical across `.claude/` and `.codex/`. Only the dispatch section legitimately differs. `just check-sync` is the gate.
- **[GENERIC] Single-level delegation** — each lens is a leaf agent. No nested fan-out. The orchestrator is the skill itself.
- **[GENERIC] Context isolation** — every lens prompt opens with the explicit "You have NOT been part of the conversation" clause. The dispatch must not leak parent transcript content.
- **[GENERIC] Cost discipline** — model assignments mix `opus` / `sonnet` / `haiku` per the table above. Surface the cost expectation in the skill description (auto-trigger metadata), not just the body. Optionally support a `--fast` arg that runs a single combined lens for users who explicitly opt out.
- **[GENERIC] Explore scope** — produces structured facts only; main agent owns plan prose. Facts land above the review marker at `create` time only.
- **[GENERIC] Rubric** — review-plan and dev-plan each ship a `rubric.md` mirroring deep-review's gradeable-criteria pattern. The orchestrator self-checks output against the rubric before presenting findings.
- **[CLAUDE] Dispatch idiom** — parallel `Agent` calls with `model` set per role.
- **[CODEX] Dispatch idiom** — `spawn_agent` with in-session sequential fallback when unavailable, mirroring the deep-review pattern.

## Implementation Checklist

Phases that touch one harness commit `.claude/` and `.codex/` together so intermediate commits do not break `just check-sync`. Each phase below names every file it touches.

### Phase 1: [GENERIC] Lens contract + rubrics

**Impl files:** `.claude/skills/review-plan/rubric.md, .codex/skills/review-plan/rubric.md, .claude/skills/dev-plan/rubric.md, .codex/skills/dev-plan/rubric.md`
**Test files:** N/A (skill is prose; no executable tests)
**Test command:** `just check-sync`

- Author the four lens prompt bodies (architecture, sequencing, spec-and-testing, codebase-claims) — these are the byte-identical generic bodies shared across harnesses.
- Author the finding-schema spec and merge-by-severity logic in prose.
- Create `rubric.md` for review-plan (lens-output gradeable criteria) and `rubric.md` for dev-plan (Explore-output gradeable criteria), mirroring the deep-review rubric pattern.
- Drop these rubrics into both `.claude/skills/<skill>/rubric.md` and `.codex/skills/<skill>/rubric.md` simultaneously so `check-sync` sees parity.

### Phase 2: [CLAUDE] review-plan parallel-Agent dispatch

**Impl files:** `.claude/skills/review-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`
**Validation cmd:** `just lint-scripts`

- Replace single-subagent dispatch with four parallel `Agent` calls; set `model` per role (`opus` for architecture/sequencing/spec-and-testing, `haiku` for codebase-claims).
- Embed the generic lens prompt bodies and finding schema from Phase 1.
- Reference `rubric.md` for the orchestrator self-check.
- Update "Why This Exists" and "Delegation Pattern" prose to reflect parallel lenses.
- Preserve review-marker logic verbatim.
- Add cost note to the skill description (auto-trigger metadata) plus a longer "Cost" section in the body.
- Optional: add `--fast` arg that collapses to a single combined lens.

### Phase 3: [CODEX] review-plan spawn_agent dispatch with in-session fallback

**Impl files:** `.codex/skills/review-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`

> Codex maintainer reviews this phase independently. The lens prompts, finding schema, and rubric reference are generic (shipped in Phase 1) and must not diverge.

- Replace single-subagent dispatch with `spawn_agent` invocation per lens (model per role) and an in-session sequential fallback when `spawn_agent` is unavailable, mirroring `.codex/skills/deep-review/SKILL.md`.
- Embed the same generic lens prompt bodies and finding schema as Phase 2.
- Reference `rubric.md` for the orchestrator self-check.
- Preserve review-marker logic verbatim.
- Add cost note in description and body.

### Phase 4: [CLAUDE] dev-plan Explore subagent

**Impl files:** `.claude/skills/dev-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`

- Add an Explore step to the `create` workflow: one `Agent` call with isolated context, `model: sonnet`, before drafting Technical Specifications / Files-to-Modify.
- Embed the generic Explore prompt (structured-fact contract from Phase 1).
- State explicitly: Explore facts land **above the review marker** in the immutable contract, and **only on `create`** — never on `update` / `complete`.
- Reference `rubric.md` for self-check on Explore output before weaving facts into plan prose.

### Phase 5: [CODEX] dev-plan Explore equivalent

**Impl files:** `.codex/skills/dev-plan/SKILL.md`
**Test files:** N/A
**Test command:** `just check-sync`

> Codex maintainer reviews this phase independently.

- Add the same Explore step using `spawn_agent` if available, otherwise inline fact-gathering with the same prompt + structured-fact contract.
- Same scope rules: above the marker, create-only.

### Phase 6: [GENERIC] Docs, promotion, manual verification

**Impl files:** `README.md`, `AGENTS.md`, `.codex/AGENTS.md`
**Test files:** N/A
**Test command:** `just check-sync && just lint-scripts`

- Update skill descriptions in repo-root `README.md` / `AGENTS.md` (descriptive surfaces).
- Verify `.codex/AGENTS.md` parity with global `~/.codex/AGENTS.md` per `scripts/check-sync.sh` rules.
- Run `/update-docs` to catch stale references.
- **Manual verification (deterministic):** create a throwaway plan referencing 3 fictitious paths; verify codebase-claims lens flags exactly those at Critical severity. Delete the throwaway plan after.
- **Manual verification (dogfooding):** run `/review-plan` against this very plan once Phase 2 has landed; run `/dev-plan create feature dummy-test` once Phase 4 has landed.
- Final `just check-sync` to confirm mirror parity.

## Technical Specifications

### Files to Modify
- **[CLAUDE]** `.claude/skills/review-plan/SKILL.md` — parallel-Agent dispatch
- **[CODEX]** `.codex/skills/review-plan/SKILL.md` — `spawn_agent` + in-session fallback
- **[CLAUDE]** `.claude/skills/dev-plan/SKILL.md` — Explore Agent call on `create`
- **[CODEX]** `.codex/skills/dev-plan/SKILL.md` — Explore equivalent on `create`
- **[GENERIC]** `README.md`, `AGENTS.md`, `.codex/AGENTS.md` — descriptive surfaces

### New Files to Create
- **[GENERIC]** `.claude/skills/review-plan/rubric.md` and `.codex/skills/review-plan/rubric.md` — byte-identical
- **[GENERIC]** `.claude/skills/dev-plan/rubric.md` and `.codex/skills/dev-plan/rubric.md` — byte-identical

### Architecture Decisions
- **[GENERIC] Four lenses** — matches deep-review's cardinality; each lens has a distinct scope. `codebase-claims` is the cheap factual lens; the other three are judgment-heavy.
- **[GENERIC] Lens bodies inline in SKILL.md, criteria in rubric.md** — same shape as deep-review.
- **[GENERIC] dev-plan stays single-subagent** — fact-gathering, not adversarial review.
- **[GENERIC] Mixed model assignment** — `opus` for the three judgment lenses, `haiku` for codebase-claims (factual lookup), `sonnet` for the dev-plan Explore subagent. Cost ≈ 3× opus + 1× haiku for review-plan, 1× sonnet for dev-plan create.
- **[CLAUDE] Dispatch:** parallel `Agent` tool calls with `model` set per role.
- **[CODEX] Dispatch:** `spawn_agent` per lens with in-session sequential fallback (mirrors `.codex/skills/deep-review/SKILL.md`).

### Dependencies
- None new.

### Integration Seams

| Seam | Scope | Writer | Caller | Contract |
|------|-------|--------|--------|----------|
| Lens finding schema | [GENERIC] | each lens prompt | orchestrator merge | `{category, severity, finding, evidence, suggestion}`; severity ∈ {Critical, Important, Minor} |
| Explore facts | [GENERIC] | dev-plan Explore | dev-plan main agent | Structured facts only (paths, patterns, dependency versions); no prose, no plan drafting |
| Rubric reference | [GENERIC] | rubric.md | orchestrator self-check | Self-check before findings are presented; identical criteria across mirrors |
| Mirror parity | [GENERIC] | .claude edits | .codex edits | Lens bodies, finding schema, rubric content byte-identical; only the dispatch section diverges |
| Claude dispatch | [CLAUDE] | review-plan / dev-plan SKILL.md | Agent tool | Parallel calls with isolated context, `model` set per role |
| Codex dispatch | [CODEX] | review-plan / dev-plan SKILL.md | spawn_agent or in-session | Same prompts and schema regardless of path; fallback path documented inline |

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

- **[GENERIC]** Four lens prompts, finding schema, and `rubric.md` files are byte-identical between `.claude/` and `.codex/`. `just check-sync` is clean.
- **[GENERIC]** Each lens prompt opens with the explicit "You have NOT been part of the conversation" clause.
- **[GENERIC]** Model assignment matches the table: opus / opus / opus / haiku for review-plan lenses, sonnet for dev-plan Explore.
- **[GENERIC]** review-plan and dev-plan each ship a `rubric.md` referenced from SKILL.md.
- **[GENERIC]** Cost expectation surfaced in the skill description string, not just the body.
- **[GENERIC]** Review marker write/validate logic unchanged and idempotent.
- **[GENERIC]** dev-plan Explore facts land above the marker on `create` only; `update` / `complete` do not re-explore.
- **[GENERIC]** Manual codebase-claims test against a throwaway plan with 3 fictitious paths flags exactly those at Critical.
- **[CLAUDE]** review-plan dispatches four parallel `Agent` calls with isolated context.
- **[CLAUDE]** dev-plan Explore is one `Agent` call with isolated context, model `sonnet`.
- **[CODEX]** review-plan dispatches via `spawn_agent` when available, with in-session sequential fallback that uses identical prompts and schema.
- **[CODEX]** dev-plan Explore uses `spawn_agent` when available, otherwise inline fact-gathering with the same prompt/schema.
- Code reviewed (`/review`, `/security-review`, `/deep-review`) and approved before merge.

<!-- reviewed: YYYY-MM-DD @ <hash> -->
<!-- /review-plan writes the marker line above. Everything below is the workspace: edits here do NOT invalidate the marker. -->

## Progress

- [ ] Phase 1: [GENERIC] Lens contract + rubrics
- [ ] Phase 2: [CLAUDE] review-plan parallel-Agent dispatch
- [ ] Phase 3: [CODEX] review-plan spawn_agent dispatch with in-session fallback
- [ ] Phase 4: [CLAUDE] dev-plan Explore subagent
- [ ] Phase 5: [CODEX] dev-plan Explore equivalent
- [ ] Phase 6: [GENERIC] Docs, promotion, manual verification

## Findings

- (append findings here as work proceeds)

## Issues & Solutions

(none yet)

## Final Results

(fill on completion)
