# Task: Align local skills with Managed Agents conventions

**Status**: In Progress
**Branch**: feature/managed-agents-alignment
**Created**: 2026-04-14

## Objective

Bring the local skill library into alignment with the Claude Managed Agents platform conventions so the same SKILL.md files could later be uploaded as custom skills with no structural rework, while also improving local Claude Code skill selection today.

## Context

The Managed Agents platform documents explicit conventions for custom skills: third-person descriptions, SKILL.md body under 500 lines, progressive disclosure with one-level-deep references, and optional rubrics for outcome-graded sessions. Most of these are useful locally regardless of whether we ever push skills to the platform — Claude Code uses the same frontmatter format for skill discovery, and the same token-budget pressures apply.

Separate tidy-up: the `deep-review` Phase 1 "Confirm Cost" gate asks for user confirmation before spawning lenses. In practice this has never been declined, and the user can always Ctrl+C mid-execution, so the gate is pure friction.

## Requirements

- Descriptions use third-person voice and include both what + when
- All SKILL.md bodies stay under 500 lines
- `deep-review` and `spec-compliance` ship with a rubric.md capturing gradeable criteria
- `deep-review` no longer blocks on confirmation before spawning lenses
- Multi-agent delegation pattern is documented explicitly in the two skills that use it
- Changes propagate to `~/.claude/skills/` via `just promote-skills`

## Review Focus

- Description format compliance (third person, trigger terms, <1024 chars)
- Rubric files use gradeable criteria ("The X contains Y") not vague language
- No behavioral regression in deep-review's lens dispatch

## Implementation Checklist

### Phase 1: Description audit
- [ ] Rewrite `dev-plan` description to third person
- [ ] Rewrite `fan-out` description to third person
- [ ] Rewrite `review-plan` description to third person
- [ ] Rewrite `rfc-finder` description to third person
- [ ] Rewrite `spec-compliance` description to third person
- [ ] Rewrite `update-docs` description to third person
- [ ] Restructure `content-draft` to lead with what it does
- [ ] Restructure `content-review` to lead with what it does
- [ ] Leave `deep-review` description as-is (already compliant)

### Phase 2: Line-count verification
- [x] Confirm all SKILL.md under 500 lines (max observed: deep-review at 351)

### Phase 3: Rubric files
- [ ] Create `.claude/skills/deep-review/rubric.md`
- [ ] Create `.claude/skills/spec-compliance/rubric.md`
- [ ] Reference rubrics from SKILL.md bodies

### Phase 4: Multi-agent pattern documentation
- [ ] Add short "Delegation pattern" note to `deep-review/SKILL.md`
- [ ] Add equivalent note to `review-plan/SKILL.md`

### Phase 5: Remove confirmation gate
- [ ] Drop "Phase 1: Confirm Cost" from `deep-review/SKILL.md`
- [ ] Replace with a single-line status announcement (no wait)

### Phase 6: Propagate and commit
- [ ] `just promote-skills` to sync to `~/.claude/skills/`
- [ ] `just check-sync` to verify
- [ ] Commit and open PR

## Technical Specifications

### Files to Modify

- `.claude/skills/content-draft/SKILL.md` - description rewrite
- `.claude/skills/content-review/SKILL.md` - description rewrite
- `.claude/skills/dev-plan/SKILL.md` - description rewrite
- `.claude/skills/fan-out/SKILL.md` - description rewrite
- `.claude/skills/review-plan/SKILL.md` - description rewrite + delegation note
- `.claude/skills/rfc-finder/SKILL.md` - description rewrite
- `.claude/skills/spec-compliance/SKILL.md` - description rewrite + rubric reference
- `.claude/skills/update-docs/SKILL.md` - description rewrite
- `.claude/skills/deep-review/SKILL.md` - remove Confirm Cost phase + rubric reference + delegation note

### New Files to Create

- `.claude/skills/deep-review/rubric.md` - gradeable criteria for the 5 lenses
- `.claude/skills/spec-compliance/rubric.md` - gradeable criteria for compliance reports

### Architecture Decisions

- **Keep SKILL.md format unchanged.** The existing format is already compatible with Managed Agents custom skills. No new fields or structural changes.
- **Rubrics are reference files, not inline content.** Keeps SKILL.md bodies short and makes rubrics reusable as Managed Agents outcome rubrics without duplication.
- **No upload-skills.sh yet.** Per discussion, the upload script is the one step that's Managed-Agents-only. Deferred until the user actually adopts the platform.

## Acceptance Criteria

- [ ] All 9 skill descriptions are third-person
- [ ] All 9 SKILL.md bodies under 500 lines
- [ ] Rubric files exist and are referenced from SKILL.md
- [ ] deep-review no longer prompts for confirmation before spawning lenses
- [ ] `just check-sync` passes after `just promote-skills`
- [ ] PR opened against main
