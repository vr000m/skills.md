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

## Implementation Checklist

### Phase 1: [Phase Name]
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

### Phase 2: [Phase Name]
- [ ] Task 1
- [ ] Task 2

### Phase 3: [Phase Name] (if needed)
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
