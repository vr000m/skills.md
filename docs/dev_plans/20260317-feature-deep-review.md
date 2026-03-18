# deep-review Skill

| Field | Value |
|-------|-------|
| **Status** | Not Started |
| **Priority** | High |
| **Branch** | `feature/deep-review` |
| **Created** | 2026-03-17 |
| **Objective** | Create a `/deep-review` skill that spawns parallel subagents with clean context to perform thorough, multi-lens code review — catching issues that single-pass, context-polluted reviews miss |

## Context

Current review workflow relies on Claude's built-in `/review` and `/security-review`, run manually (often multiple times) within a conversation whose context is polluted by implementation history. The model that wrote the code is biased when reviewing it. Across projects (code-mcp, kai-pipecat), this results in 2-3 manual review rounds to surface all issues.

gstack (github.com/garrytan/gstack) demonstrates the value of cognitive mode separation — distinct skills for distinct phases. Their `/review` uses two-pass analysis, structured checklists, and Greptile triage. We adapt these ideas but go further: parallel lens-based subagents with clean context and a feedback loop that updates project knowledge.

**Key design principle:** `/deep-review` complements the built-in `/review` and `/security-review` — it does not wrap or replace them. Users can run either or both.

## Requirements

1. Spawn parallel subagents (clean context, no parent conversation history) for thorough review
2. Each subagent reviews through a specific lens (logic, security, spec compliance, architecture, documentation)
3. Findings include severity, category, file:line, evidence, and actionable suggestion
4. Suppress previously-dismissed findings using AGENTS.md `## Review Checklist`
5. Flag documentation gaps alongside code issues
6. Consolidated report presented to main context for triage
7. Triage outcomes (won't-fix, analysis-error) feed back into AGENTS.md `## Review Checklist`
8. Dev-plan template gains a `## Review Focus` section for author-specified review criteria (including spec references)
9. Works across project types (Python, JS/TS, shell, mixed)
10. Coexists with built-in `/review` and `/security-review` — distinct name, distinct purpose
11. Cost-appropriate model assignment per lens (opus for deep analysis, sonnet/haiku for lighter tasks)
12. Partial failure handling with `--continue` flag to retry only failed lenses

## Implementation Checklist

### Phase 1: Core skill — `.claude/skills/deep-review/SKILL.md`
- [ ] Create skill file with frontmatter (name, description, argument-hint)
- [ ] Define input resolution: explicit path/PR > current branch diff > ask user
- [ ] Define 5 review lenses with per-lens subagent prompts:
  - [ ] **Logic lens** (model: opus): off-by-one, edge cases, error handling, race conditions, resource leaks
  - [ ] **Security lens** (model: opus): OWASP top 10, input validation, secrets exposure, auth/authz
  - [ ] **Spec compliance lens** (model: opus): RFC/standard conformance — only runs when dev-plan `## Review Focus` lists specs/RFCs
  - [ ] **Architecture lens** (model: sonnet): coupling, API surface, backward compat, naming, patterns
  - [ ] **Documentation lens** (model: haiku): stale docs, missing coverage, plan-vs-implementation drift, README/AGENTS.md gaps
- [ ] Define finding format: severity (Critical/Important/Minor), category, file:line, evidence, suggestion
- [ ] Define triage flow: findings → main context → fix / won't-fix (+ why) / analysis-error (+ correction)
- [ ] Define feedback loop: won't-fix and analysis-error outcomes update AGENTS.md `## Review Checklist`
- [ ] Define suppression: before presenting, check AGENTS.md `## Review Checklist` for previously-dismissed patterns
- [ ] Define deduplication: when multiple lenses flag the same file:line, keep the higher-severity finding and note the overlap
- [ ] Define `--continue` flag: retry only lenses that failed/timed out in the previous run, merge with prior results
- [ ] Define `--full` flag (default): run all lenses fresh
- [ ] Define cost confirmation: before spawning, show user which lenses will run with which models, ask to proceed
- [ ] Subagent mechanism: use Claude Code's built-in Agent tool (like `/review-plan`), NOT CLI spawning — no worktrees needed since all lenses review the same codebase in place

### Phase 2: Dev-plan template update
- [ ] Add `## Review Focus` section to `.claude/skills/dev-plan/template.md`
- [ ] Section is optional but encouraged — author-specified criteria that `/deep-review` and `/review-plan` consume
- [ ] Must include spec/RFC references if applicable (this is how the spec compliance lens knows to activate)
- [ ] Examples: "SDP must comply with RFC 3264", "no plaintext credentials in signaling", "backward compat with v2 API"

### Phase 3: AGENTS.md convention
- [ ] Document that repos should add `## Review Checklist` to their repo-root AGENTS.md
- [ ] Checklist contains: project-specific gotchas, known false positives, won't-fix patterns with reasons
- [ ] `/deep-review` reads this section; triage outcomes update it
- [ ] Add initial `## Review Checklist` section to this repo's AGENTS.md as an example
- [ ] Format: bullet list with `- **[Category]**: [pattern] — [reason] (added YYYY-MM-DD)`

### Phase 4: Script integration
- [ ] Add `deep-review` to `MANAGED_SKILLS` in `promote-skills.sh`
- [ ] Add `deep-review` to `MANAGED_SKILLS` in `sync-skills.sh`
- [ ] Add `deep-review` to `MANAGED_SKILLS` in `bootstrap-skills.sh`
- [ ] Add `deep-review` to `MANAGED_SKILLS` in `check-sync.sh`
- [ ] Add `deep-review` to `.env.example`

### Phase 5: Documentation
- [ ] Add `deep-review` row to README.md skills table
- [ ] Update repo-root AGENTS.md skill workflow section (add `/deep-review` after implementation, before merge)
- [ ] Update dev_plans/README.md with this plan entry

### Phase 6: Codex tasks (Codex handles independently)
Codex should independently create/update the following to match its own harness conventions:
- [ ] Create `.codex/skills/deep-review/SKILL.md` — adapted from Claude version for Codex's model/platform
- [ ] Update `.codex/skills/dev-plan/template.md` — add `## Review Focus` section
- [ ] Update `.codex/AGENTS.md` — add `/deep-review` to Skill Workflow section
- [ ] Use Codex-appropriate model IDs (not Claude model names)

**Note:** Do not directly edit `.codex/skills/` — it's a mirror managed by sync scripts. Codex handles its own side.

## Technical Specifications

### Files to Create
| File | Purpose |
|------|---------|
| `.claude/skills/deep-review/SKILL.md` | Core skill definition with lens prompts and triage flow |

### Files to Modify
| File | Change |
|------|--------|
| `.claude/skills/dev-plan/template.md` | Add `## Review Focus` as optional section in plan template |
| `AGENTS.md` (repo root) | Add `## Review Checklist` section; update skill workflow |
| `README.md` | Add deep-review to skills table |
| `scripts/promote-skills.sh` | Add `deep-review` to `MANAGED_SKILLS` |
| `scripts/sync-skills.sh` | Add `deep-review` to `MANAGED_SKILLS` |
| `scripts/bootstrap-skills.sh` | Add `deep-review` to `MANAGED_SKILLS` |
| `scripts/check-sync.sh` | Add `deep-review` to `MANAGED_SKILLS` |
| `.env.example` | Add `deep-review` to `MANAGED_SKILLS` |
| `docs/dev_plans/README.md` | Add this plan to task table |

### Architecture Decisions

**Parallel lenses vs sequential cycles:**
Parallel lenses (multiple subagents, each reviewing through a different lens) outperform sequential cycles (one agent reviewing N times) because:
- Each lens has clean context optimized for its domain
- Parallelism is faster than sequential re-reviews
- Diminishing returns in sequential passes (80/15/4% rule) — different lenses catch different *categories*

**Subagent mechanism:**
Uses Claude Code's built-in Agent tool (same as `/review-plan`), NOT CLI-level spawning (unlike `/fan-out`). Rationale: all lenses review the same codebase in place — no worktrees or process isolation needed. Agent tool provides clean context naturally via `subagent_type: general-purpose`.

**Cost-tiered model assignment:**
Not all lenses need the same model. Assign based on analysis depth:
| Lens | Model | Rationale |
|------|-------|-----------|
| Logic | opus | Requires deep reasoning about edge cases and race conditions |
| Security | opus | Security bugs are high-impact; worth the investment |
| Spec compliance | opus | RFC conformance requires careful cross-referencing |
| Architecture | sonnet | Pattern matching and coupling analysis; less deep reasoning |
| Documentation | haiku | Checking doc freshness is mostly mechanical comparison |

**Lens activation:**
Not all lenses run every time:
- Logic, Architecture, Documentation: always run
- Security: always run (lightweight when no security-relevant changes)
- Spec compliance: only when the dev-plan `## Review Focus` explicitly lists specs/RFCs — the skill does NOT guess

**Partial failure and re-run behavior:**
```
/deep-review          → run all lenses (default = --full)
/deep-review --full   → run all lenses (explicit)
/deep-review --continue → retry only failed/timed-out lenses from last run, merge with prior results
```
- Timeouts: present partial results immediately with a note listing which lenses didn't complete
- No silent skipping — if a lens didn't run, the report says so explicitly
- `--continue` prevents permanently slow lenses from being silently abandoned

**Cost confirmation:**
Before spawning subagents, show the user:
```
Deep review will run 4 lenses:
  Logic (opus), Security (opus), Architecture (sonnet), Documentation (haiku)
  Spec compliance: skipped (no specs in Review Focus)
Proceed? [Y/n]
```

**Triage feedback loop:**
```
Finding → User triages:
  ├── "Fix" → user/agent fixes the code
  ├── "Won't fix" → reason recorded in AGENTS.md ## Review Checklist
  │   (future deep-reviews suppress this pattern with a note)
  └── "Analysis error" → correction recorded in AGENTS.md ## Review Checklist
      (future deep-reviews avoid this false positive)
```

**Deduplication:**
When multiple lenses flag the same file:line:
- Keep the finding with higher severity
- Note which other lenses also flagged it (adds confidence)
- Don't present the same issue twice

**Dismissed pattern storage:**
Dismissed patterns live in repo-root AGENTS.md `## Review Checklist`, not in separate memory files. Format:
```markdown
## Review Checklist
- **[Security]**: Won't fix — raw SQL in migration scripts is intentional (added 2026-03-17)
- **[Architecture]**: Analysis error — singleton pattern in transport.py is by design, not a coupling issue (added 2026-03-17)
```
This keeps all project knowledge in one place (AGENTS.md) rather than split across AGENTS.md + memory files.

**Relationship to existing skills:**
```
/dev-plan create → /review-plan → implement → /deep-review → /update-docs → merge
                                                    ↕
                                        /review + /security-review
                                        (can run independently anytime)
```

### Integration Seams

| Seam | Producer | Consumer | Contract |
|------|----------|----------|----------|
| Dev plan Review Focus | `/dev-plan` | `/deep-review`, `/review-plan` | Optional `## Review Focus` section with bullet list of criteria; must list specs/RFCs for spec compliance lens to activate |
| AGENTS.md Review Checklist | User/triage | `/deep-review` | `## Review Checklist` section in repo-root AGENTS.md with dismissed patterns |
| Finding format | Lens subagents | Main context triage | Severity/category/file:line/evidence/suggestion structure |

## Review Focus

- [ ] Subagent prompts must be self-contained — no references to parent context
- [ ] Each lens prompt must specify what to look for AND what to ignore (scope boundaries)
- [ ] Finding deduplication logic must handle overlapping categories (e.g., a security issue that's also a logic issue)
- [ ] AGENTS.md changes must not break existing sections or sync workflow
- [ ] Dev-plan template change must be backward compatible (Review Focus is optional)
- [ ] The skill must work on repos that have no AGENTS.md or no Review Checklist section (graceful degradation)
- [ ] Spec compliance lens must NOT guess — only activates when Review Focus explicitly lists specs/RFCs
- [ ] Cost confirmation must appear before spawning subagents

## Testing Notes

### Manual testing plan
1. Run `/deep-review` on this repo's own PR (self-referential test)
2. Run `/deep-review` on a pipecat PR with protocol code and Review Focus listing RFCs (tests spec compliance lens activation)
3. Run `/deep-review` on a project with no AGENTS.md (tests graceful degradation)
4. Verify triage flow: accept a finding, won't-fix a finding, flag an analysis error
5. Verify suppression: run again after won't-fix, confirm suppressed finding noted but not resurfaced
6. Verify partial failure: simulate a lens timeout, confirm partial results presented with note
7. Verify `--continue`: after partial failure, run with `--continue`, confirm only failed lenses re-run
8. Verify cost confirmation: confirm user sees lens/model breakdown before spawning

## Issues & Solutions

### Review finding: template.md vs SKILL.md
- **Problem**: Original plan targeted `.claude/skills/dev-plan/SKILL.md` for Review Focus section
- **Solution**: Corrected to `.claude/skills/dev-plan/template.md` — SKILL.md describes behavior, template.md has the section structure
- **Files affected**: Plan updated, no code change needed

### Review finding: subagent mechanism ambiguity
- **Problem**: Plan didn't specify whether to use Agent tool or CLI spawning
- **Solution**: Explicitly chose Agent tool (like `/review-plan`) — no worktrees needed since all lenses review same codebase
- **Files affected**: Plan updated

### Review finding: AGENTS.md ambiguity
- **Problem**: Plan said "AGENTS.md" without specifying repo-root vs `.codex/AGENTS.md`
- **Solution**: Clarified: repo-root AGENTS.md gets Review Checklist + workflow update. `.codex/AGENTS.md` is Codex's responsibility.
- **Files affected**: Plan updated

### Review finding: cost of 5 opus subagents
- **Problem**: No cost guard for spawning 5 opus subagents
- **Solution**: Tiered models (opus/sonnet/haiku by lens complexity) + cost confirmation before spawning
- **Files affected**: Plan updated

## Acceptance Criteria

- [ ] `/deep-review` triggers correctly from slash command
- [ ] Spawns parallel subagents with clean context (no parent history)
- [ ] At least 3 lenses produce structured findings
- [ ] Findings are deduplicated and sorted by severity
- [ ] Previously-dismissed patterns (from AGENTS.md Review Checklist) are suppressed with a note
- [ ] Triage outcomes can be recorded in AGENTS.md Review Checklist
- [ ] Works on repos without AGENTS.md Review Checklist (graceful degradation)
- [ ] Dev-plan template includes optional Review Focus section
- [ ] Spec compliance lens only activates when Review Focus lists specs/RFCs
- [ ] Cost confirmation shown before spawning subagents
- [ ] `--continue` retries only failed lenses and merges with prior results
- [ ] Skill syncs correctly via promote/sync/bootstrap/check-sync scripts
- [ ] Codex has equivalent skill adapted to its own harness (Codex handles independently)

## Final Results

*(To be filled on completion)*
