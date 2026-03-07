# Standardize Content Guidelines in Skills Repo

| Field | Value |
|-------|-------|
| Status | Complete |
| Assignee | Codex |
| Priority | High |
| Branch | `codex/content-guidelines-standardize` |
| Created | 2026-03-07 |
| Updated | 2026-03-07 |

## Objective

Make this repo the canonical home for `content-guidelines.md`, add anti-LLM authenticity rules to the drafting and review workflow, and mirror the updated skill assets into the global Codex and Claude skill directories.

## Context

The repo previously treated content guidelines as externally sourced, with script support for local and remote overrides. That made the authority model harder to reason about and kept the anti-LLM guidance split between the draft skill, the review skill, and the `varunsingh.net` repo. This change consolidates the content guidance here, strengthens the drafting constraints, and makes review enforce the same authenticity rules.

## Requirements

- `content-guidelines.md` must be canonical in this repo.
- `.codex` and `.claude` copies of `content-guidelines.md` must stay in sync.
- `content-draft` must include explicit anti-LLM authenticity constraints and a final de-LLM pass.
- `content-review` must review against those authenticity constraints, not just style and structure.
- Sync/promotion/bootstrap/check scripts must stop using `CONTENT_GUIDELINES_LOCAL` and `CONTENT_GUIDELINES_URL`.
- Repo documentation must describe the new authority model clearly.
- Updated `content-draft` and `content-review` skills must be promoted to the global Codex and Claude skill folders.

## Implementation Checklist

### Phase 1: Canonical Content Guidance

- [x] Add anti-LLM authenticity rules to `.codex/skills/content-review/references/content-guidelines.md`
- [x] Mirror the same guideline file to `.claude/skills/content-review/references/content-guidelines.md`
- [x] Add checklist items that enforce concrete openers, anchors, trade-offs, and rough-edge disclosure

### Phase 2: Skill Updates

- [x] Update `.codex/skills/content-draft/SKILL.md` with hard authenticity constraints and a de-LLM pass
- [x] Update `.claude/skills/content-draft/SKILL.md` with the same drafting rules
- [x] Update `.codex/skills/content-review/SKILL.md` so review covers AI-signalling phrases, abstraction-only prose, concrete anchors, trade-offs, and failure notes
- [x] Update `.claude/skills/content-review/SKILL.md` with the same review expectations

### Phase 3: Authority Model and Docs

- [x] Update sync scripts to treat the repo guideline file as canonical
- [x] Remove local/remote content-guideline fetch logic from scripts
- [x] Update `.env.example` to reflect repo-canonical guidelines
- [x] Update `README.md` authority model and workflow notes
- [x] Add a dedicated dev plan for this work and update the dev-plan index

### Phase 4: Validation and Promotion

- [x] Run `bash -n scripts/*.sh`
- [x] Run `shellcheck scripts/*.sh`
- [x] Run `shfmt -d scripts/*.sh`
- [x] Run `./scripts/promote-skills.sh --yes` with `MANAGED_SKILLS='content-draft content-review'`
- [x] Run `./scripts/check-sync.sh`

## Technical Specifications

### Files Modified

| File | Change |
|------|--------|
| `.codex/skills/content-draft/SKILL.md` | Add anti-LLM drafting constraints and de-LLM pass |
| `.claude/skills/content-draft/SKILL.md` | Mirror draft skill updates |
| `.codex/skills/content-review/SKILL.md` | Expand review scope to enforce authenticity signals |
| `.claude/skills/content-review/SKILL.md` | Mirror review skill updates |
| `.codex/skills/content-review/references/content-guidelines.md` | Canonical guideline file with anti-LLM rules |
| `.claude/skills/content-review/references/content-guidelines.md` | Mirror canonical guideline file |
| `scripts/sync-skills.sh` | Preserve repo-canonical guideline file on sync |
| `scripts/promote-skills.sh` | Copy canonical guideline file to global skill dirs |
| `scripts/bootstrap-skills.sh` | Copy canonical guideline file on bootstrap |
| `scripts/check-sync.sh` | Validate repo/global guideline copies against repo canonical |
| `.env.example` | Remove external guideline-source configuration |
| `README.md` | Document repo-canonical guideline authority |
| `docs/dev_plans/README.md` | Add this work item to completed tasks |

### Authority Decision

- Canonical source: `.codex/skills/content-review/references/content-guidelines.md`
- Repo mirror: `.claude/skills/content-review/references/content-guidelines.md`
- Global mirrors:
  - `~/.codex/skills/content-review/references/content-guidelines.md`
  - `~/.claude/skills/content-review/references/content-guidelines.md`

### Anti-LLM Rules Added

- Concrete-first openers
- Evidence density per major section
- Required trade-off disclosure
- Required failure/adjustment disclosure
- Ban on common AI-signalling template phrases
- Removal of assistant-meta residue
- Mandatory final de-LLM pass before output

## Testing Notes

Executed:

- `bash -n scripts/*.sh` (pass)
- `shellcheck scripts/*.sh` (pass)
- `shfmt -d scripts/*.sh` (pass)
- `MANAGED_SKILLS='content-draft content-review' ./scripts/promote-skills.sh --yes` (pass)
- `./scripts/check-sync.sh` (pass)

## Issues & Solutions

- Issue: `check-sync` failed before promotion because the global skill folders still contained the older draft/review skill copies.
- Solution: Promote only `content-draft` and `content-review` to global, then re-run `check-sync`.

- Issue: The repo had no dedicated dev plan for this standardization work, which made later review less precise.
- Solution: Add this plan file and update `docs/dev_plans/README.md`.

## Acceptance Criteria

- [x] Drafting rules explicitly discourage generic AI-sounding output
- [x] Review rules can detect and flag those same authenticity failures
- [x] Repo docs describe this repo as the guideline authority
- [x] Scripts no longer depend on external content-guideline sources
- [x] Global Codex and Claude skill folders received the updated skill copies
- [x] Validation commands completed successfully
- [x] A dedicated dev plan exists for downstream review

## Final Results

This repo now owns the content-guideline authority. The draft and review skills both enforce anti-LLM authenticity constraints, the sync tooling mirrors the canonical guideline file outward instead of pulling it in from elsewhere, and the updated skill copies have already been promoted to the global Codex and Claude skill folders.
