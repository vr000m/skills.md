---
name: dev-plan
description: Creates and updates development plans for multi-component features, architecture changes, and complex work. Use when work affects 3+ files, involves UI/UX changes, database migrations, or is estimated at 2+ hours, or when the user says "dev plan", "plan this", or "/dev-plan".
argument-hint: [action] [type] [name]
---

# Development Plan Skill

Create, update, and manage development plans for complex work.

## Usage

- `/dev-plan create feature auth-system` - Create a new feature plan
- `/dev-plan create bug login-redirect` - Create a bug fix plan
- `/dev-plan update` - Update the current/most recent plan
- `/dev-plan complete` - Mark plan as complete, fill final sections
- `/dev-plan list` - List existing plans

## When to Create a Plan

Create a development plan when:
- Multi-component features (affecting 3+ files or systems)
- UI/UX changes with significant user impact
- Database schema changes or migrations
- Architecture improvements or refactoring
- Integration work (new APIs, external services)
- Bug fixes requiring multiple coordinated changes
- Any work estimated to take 2+ hours

## Plan Location & Naming

**Location:** `./docs/dev_plans/` (create directory if missing)

**Naming convention:**
```
docs/dev_plans/yyyymmdd-type-name.md
```

**Types:** `feature`, `bug`, `chore`, `docs`, `design`, `refactor`

**Examples:**
- `20260201-feature-user-authentication.md`
- `20260201-bug-login-redirect-loop.md`
- `20260201-refactor-api-consolidation.md`

## Branch Policy

Before creating a plan, check the current branch:
1. If on `main` or `master`, suggest creating a feature branch first
2. Recommend branch naming: `type/brief-name` (e.g., `feature/auth-system`)
3. Record the working branch in the plan header

## Required Sections

Every plan must include these sections (see template.md for full format):

1. **Header** - Status, assignee, priority, branch, dates, objective
2. **Context** - Background, why this work is needed
3. **Requirements** - Specific requirements and constraints
4. **Implementation Checklist** - Phased breakdown with checkboxes. Each phase should include a contract block directly under the heading with `**Impl files:**`, `**Test files:**`, `**Test command:**` (in backticks), and optionally `**Validation cmd:**` (in backticks, runs after tests pass, failure hands back to user). `/conduct` reads these to decide how to spawn subagents and run tests/validation. Phases may also include a `**Findings:**` subsection the implementer appends to during execution — use it to persist diagnostic query results (with filters explicit), decision rationale, and accepted-behaviour outcomes. Omit all slots only when the phase is not `/conduct`-driven; if every phase omits them, `/conduct` emits a degraded-mode warning.
5. **Technical Specifications** - Files to modify, interfaces, architecture decisions, integration seams
6. **Testing Notes** - Test approach and results
7. **Issues & Solutions** - Problems encountered and how resolved
8. **Acceptance Criteria** - Definition of done (checkboxes)
9. **Final Results** - Summary of outcomes when complete

## Review Focus

Plans may include an optional `## Review Focus` section to guide `/review-plan` and `/deep-review`.

Use it to capture the review criteria the author already knows matter:
- Exact spec or RFC references
- Backward-compatibility constraints
- High-risk code paths or integration seams
- Known trade-offs or areas that deserve a second look

Keep it short, concrete, and specific. If a plan references external standards, name them explicitly so downstream review tooling can activate the spec-compliance lens instead of guessing.

## Workflow

### Pre-Implementation
1. Check branch (suggest feature branch if on main)
2. Create plan with initial structure
3. Define phases and acceptance criteria
4. Identify files to modify, potential risks, and any Review Focus items that should be written into the plan
5. Run `/review-plan` to audit for gaps, undocumented assumptions, missing constraints, and Review Focus coverage before coding starts
6. Address review findings, then proceed to implementation. For a linear multi-phase plan, run `/conduct <plan>` to walk phases with per-phase clean-context subagents (fill the `**Impl files:**`, `**Test files:**`, `**Test command:**`, and optional `**Validation cmd:**` slots so the conductor can decide spawn strategy and run tests/validation). Use `/fan-out` when phases are independent enough to parallelise.

### During Implementation
1. Update checkboxes as tasks complete
2. Document issues immediately when encountered
3. Update technical specifications if approach changes
4. Add testing results as validation is performed
5. When using `/fan-out`, fill in the **Integration Seams** table before fanning out — it tells agents what contracts to honor and tells the merge phase what to verify
6. When using `/deep-review`, make sure the plan's `## Review Focus` section is current before starting the review pass

### Post-Implementation
1. Mark status as Complete
2. Fill in final testing results
3. Document outcomes and learnings
4. Run `/deep-review` before merge to catch issues that slipped through implementation
5. Update README.md task table if one exists in docs/dev_plans/

## Status Values

- `Not Started` - Plan created but work hasn't begun
- `In Progress` - Actively working on implementation
- `Blocked` - Waiting on external dependency or decision
- `Complete` - All acceptance criteria met

## README.md Task Table

If `docs/dev_plans/README.md` exists, update the task tables:
- Move completed tasks to "Completed Tasks" table
- Keep "Current Tasks" table up to date
