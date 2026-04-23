# Development Plan Template

Use this template when creating new development plans.

---

# Task: [Title]

**Status**: Not Started | In Progress | Blocked | Complete
**Assigned to**: [Agent/Person]
**Priority**: High | Medium | Low
**Branch**: [branch-name]
**Created**: YYYY-MM-DD
**Completed**: YYYY-MM-DD (fill when done)

## Objective

[One or two sentences describing what needs to be accomplished]

## Context

[Background information explaining why this work is needed. Include:
- What problem this solves
- How it fits into the larger project
- Any relevant history or prior attempts]

## Requirements

[Specific requirements and constraints for this work]

- Requirement 1
- Requirement 2
- Requirement 3

## Review Focus

[Optional review criteria for `/review-plan` and `/deep-review`. Include spec or RFC references here if they matter.]

- Focus item 1
- Focus item 2
- RFC/spec references, if applicable

## Implementation Checklist

Each phase SHOULD include a short contract block directly under the heading. These slots are consumed by `/conduct` to decide how to spawn subagents and run tests. Fill them in **every** phase you expect `/conduct` to execute — a phase with no slots falls through to degraded mode (sequential spawn + test fallback) and forfeits the parallel implementer/test-writer split.

- `**Impl files:**` — comma-separated paths or globs the implementer will touch (e.g., `src/foo.py, src/bar/*.ts`)
- `**Test files:**` — comma-separated paths or globs the test-writer will create/modify
- `**Test command:**` — the single canonical test invocation for this phase, in backticks (e.g., ``**Test command:** `pytest tests/test_foo.py -v` ``)
- `**Validation cmd:**` *(optional)* — a post-test check that runs after tests pass, before the boundary commit, in backticks (e.g., ``**Validation cmd:** `python scripts/reprocess_and_diff.py --ids X,Y` ``). Failure hands back to the user rather than triggering a fix loop. Use for reprocess-and-diff against a live DB, staging API probes, or other behaviour an implementer cannot auto-repair.

If `Impl files:` and `Test files:` overlap, `/conduct` falls back to sequential spawning for that phase. If any slot is absent, `/conduct` falls back to safe defaults (sequential spawn, resolve test command from repo defaults or `--test-cmd`). If *every* unfinished phase is missing every slot, `/conduct` emits a degraded-mode warning on the first handback.

Each phase MAY include an optional `**Findings:**` subsection for durable notes that should survive after the run: diagnostic query results (with explicit filters stated), decision rationale, and any "checked / accepted behaviour" outcomes. For `/conduct`-driven work, do not rely on subagents to append to the reviewed plan during the run; keep live execution notes in conduct handbacks/state, then copy durable conclusions into `**Findings:**` when you intentionally update the plan.

### Phase 1: [Phase Name]

**Impl files:** path/to/foo.ts, path/to/bar.ts
**Test files:** tests/test_foo.ts
**Test command:** `npm test -- tests/test_foo.ts`
**Validation cmd:** `npm run smoke -- --env staging`

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Findings:**
- (implementer appends query results, decision rationale, or accepted-behaviour notes here as work proceeds)

### Phase 2: [Phase Name]

**Impl files:** ...
**Test files:** ...
**Test command:** `...`

- [ ] Task 1
- [ ] Task 2

### Phase 3: [Phase Name] (if needed)

**Impl files:** ...
**Test files:** ...
**Test command:** `...`

- [ ] Task 1
- [ ] Task 2

## Technical Specifications

### Files to Modify
- `path/to/file1.ts` - [what changes]
- `path/to/file2.ts` - [what changes]

### New Files to Create
- `path/to/new-file.ts` - [purpose]

### Architecture Decisions
- Decision 1: [rationale]
- Decision 2: [rationale]

### Dependencies
- [Any new dependencies or integrations]

### Integration Seams

Cross-component boundaries where one task's output feeds into another's input.
Fill this in before using `/fan-out` — it tells each agent what contracts to honor
and tells the merge phase what to verify.

| Seam | Writer (task) | Caller (task) | Contract |
|------|---------------|---------------|----------|
| [e.g., cleanup on refresh] | [IndexStore] | [cli.py] | [Must delete stale records before upsert] |

For each seam, consider: who calls it, resource lifecycle (open/close), error paths, and idempotency.

## Testing Notes

### Test Approach
- [ ] Unit tests for [component]
- [ ] Integration tests for [flow]
- [ ] Manual testing of [scenario]

### Test Results
- [ ] All existing tests pass
- [ ] New tests added and passing
- [ ] Manual verification complete

### Edge Cases Tested
- [ ] Edge case 1
- [ ] Edge case 2

## Issues & Solutions

### Issue 1: [Brief description]
- **Problem**: [What went wrong]
- **Solution**: [How it was resolved]
- **Files affected**: [List files]

### Issue 2: [Brief description]
- **Problem**: [What went wrong]
- **Solution**: [How it was resolved]
- **Files affected**: [List files]

## Acceptance Criteria

- [ ] Criterion 1 - [specific, measurable outcome]
- [ ] Criterion 2 - [specific, measurable outcome]
- [ ] Criterion 3 - [specific, measurable outcome]
- [ ] Code reviewed and approved
- [ ] Tests passing
- [ ] Documentation updated (if applicable)

## Final Results

[Fill this section when the work is complete]

### Summary
[Brief summary of what was accomplished]

### Outcomes
- Outcome 1
- Outcome 2

### Learnings
- [Any insights or lessons learned during implementation]

### Follow-up Work
- [Any related work identified for future plans]
