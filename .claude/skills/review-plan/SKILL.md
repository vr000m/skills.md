---
name: review-plan
description: Reviews a development plan for gaps, undocumented assumptions, missing constraints, and architectural risks before implementation begins. Spawns a fresh-context subagent that audits the plan against the actual codebase. Use after a dev-plan is created, when the user says "review plan", "audit plan", "check plan", or "/review-plan", and proactively after the dev-plan skill produces a new plan file.
argument-hint: "[path/to/plan.md]"
---

# Review Plan: Independent Plan Audit

Spawn a fresh-context subagent to audit a development plan before implementation begins. The subagent has no knowledge of the conversation that produced the plan — this is intentional. A reviewer who didn't write the plan catches what the author's blind spots miss.

## Why This Exists

Plans encode assumptions. Some are stated, most aren't. The author knows what they meant; a fresh reader sees only what's written. This skill exploits that gap: an independent agent reads the plan cold, explores the codebase to verify claims, and surfaces what's missing, ambiguous, or risky. Findings go back to the user for discussion — the plan *body* is never modified automatically. The sole exception is a trailing **review marker footer** appended after the user explicitly accepts or waives findings, consumed by `/conduct` as a readiness signal.

## Delegation Pattern

This skill spawns a single subagent with **isolated context** — no parent conversation history, only the plan content and codebase access. This is the same pattern that maps to Managed Agents `callable_agents`: an orchestrator (this skill) delegates a well-scoped task to a worker with its own context window, and only sees the worker's final report. The reviewer does not spawn further subagents (one level of delegation only).

## When to Run

- **After `/dev-plan create`** — this is the primary trigger. Run automatically, blocking, before implementation starts.
- **Manually via `/review-plan [path]`** — when the user wants to audit a plan mid-cycle or re-check after updates.
- **Before `/fan-out`** — if a plan hasn't been reviewed yet, catch gaps before parallelizing work across agents.

## Path Resolution

1. If a path argument is provided, use it directly
2. If no path is provided, scan `docs/dev_plans/` for the most recent `.md` file by modification time
3. If triggered right after `/dev-plan`, the plan path is already in conversation context — use it
4. If no plan is found, tell the user and ask for a path

## Execution

### Step 1: Read the Plan

Read the full plan file. Extract:
- The objective and requirements
- The implementation checklist (phases, tasks)
- Technical specifications (files to modify, interfaces, architecture decisions)
- Review Focus (if present, including any explicit spec or RFC references)
- Integration seams (if present)
- Acceptance criteria
- Any stated constraints

### Step 2: Spawn the Review Agent

Spawn a single subagent with these characteristics:
- **Type**: `general-purpose`
- **Model**: `opus` (extended thinking is the point — invest tokens now to save rework later)
- **Blocking**: Yes — wait for the result before continuing
- **Context isolation**: The subagent gets ONLY the plan content and the codebase. It does NOT get the parent conversation history.

Build the subagent prompt using this template:

```
You are an independent reviewer auditing a development plan before implementation begins.
You have NOT been part of the conversation that produced this plan. This is intentional —
your job is to catch what the author missed.

## The Plan

<plan>
{{PLAN_CONTENT}}
</plan>

## Review Focus

{{REVIEW_FOCUS}}

## Your Task

Audit this plan by doing the following:

1. **Read the plan carefully.** Understand the objective, requirements, tasks, and technical specs.

2. **Explore the codebase.** Validate every assumption the plan makes:
   - Do the files listed in "Files to Modify" actually exist? Are the paths correct?
   - Do the APIs, functions, classes, or patterns referenced in the plan exist in the codebase?
   - Does the project structure match what the plan assumes?
   - Are the dependencies the plan relies on actually available?
   - Check package.json / pyproject.toml / Cargo.toml etc. for dependency versions
   - If the plan includes a `Review Focus` section, use it as the authoritative source for extra constraints and spec/RFC references.

3. **Identify gaps.** Look for:
   - **Undocumented assumptions** — things the plan takes for granted but doesn't state
   - **Missing constraints** — limits, edge cases, or failure modes not addressed
   - **Ambiguous requirements** — statements that could be interpreted multiple ways
   - **Architectural risks** — patterns that conflict with the existing codebase, scaling concerns, or coupling issues
   - **Sequencing problems** — tasks ordered wrong, or dependencies between "independent" tasks
   - **Missing tasks** — work that's clearly needed but not listed (e.g., migrations, config changes, docs)
   - **Testing gaps** — scenarios not covered by the testing plan
   - **Integration seam risks** — boundaries where independently-built pieces must connect

4. **Produce findings.** For each issue found, provide:
   - **Category**: one of [Assumption, Constraint, Ambiguity, Risk, Sequencing, Missing Task, Testing Gap]
   - **Severity**: Critical (blocks implementation), Important (likely causes rework), Minor (nice to address)
   - **Finding**: What the issue is
   - **Evidence**: What you found in the codebase that supports this finding
   - **Suggestion**: A specific constraint, clarification, or task to add to the plan

## Output Format

Return your findings as a structured list. Start with a one-line summary of overall plan quality,
then list findings grouped by severity (Critical first, then Important, then Minor).

If the plan is solid and you find no significant issues, say so — don't manufacture findings.
A clean review is a valid outcome.
```

Replace `{{PLAN_CONTENT}}` with the full text of the plan file. Replace `{{REVIEW_FOCUS}}`
with the extracted `## Review Focus` content, or `None provided.` when the section is absent.

### Step 3: Present Findings

When the subagent returns, present the findings to the user. Format them clearly:

```markdown
## Plan Review: [plan-file-name]

**Overall**: [subagent's summary line]

### Critical
- **[Category]**: [Finding]
  - Evidence: [what was found in codebase]
  - Suggestion: [what to add/change in the plan]

### Important
- ...

### Minor
- ...

---
**Next steps**: Review these findings and decide which ones to incorporate into the plan.
Update the plan with `/dev-plan update` for any accepted changes.
```

If the review is clean (no critical or important findings), say so concisely and proceed.

### Step 4: Discussion

Do NOT modify the plan *body* automatically. The findings are a starting point for conversation:
- The user may accept some findings and reject others
- Some findings may need clarification or deeper investigation
- Accepted findings should be incorporated via `/dev-plan update`

Only after the user has reviewed and addressed the findings (or explicitly decided to proceed) should implementation begin.

### Step 5: Write the Review Marker

After findings have been presented and discussed, ask the user one question:

> Are findings addressed? (`yes` / `waive` / `no`)

- **`yes`** — user has incorporated all findings they plan to address. Write the marker.
- **`waive`** — user has read the findings and chosen not to act on them. Write the marker anyway.
- **`no`** — exit without writing. User will re-run `/review-plan` later.

The **review marker** is a single HTML-comment line written into the plan file. It acts as a **divider** between the immutable contract above and the editable workspace below (`## Progress`, `## Findings`, etc.):

```
<!-- reviewed: YYYY-MM-DD @ <hash> -->
```

- `YYYY-MM-DD` — today's date.
- `<hash>` — 40-character SHA-1 from `git hash-object` of the plan content **above** the marker line. Anything on the marker line or below it is excluded from hashing. This means the user (or `/conduct`) can tick `## Progress` checkboxes or append `## Findings` after review without invalidating the marker.

Procedure:

1. Read the plan file.
2. Find the last unfenced, column-zero line matching **either** the real-marker regex `^<!-- reviewed: \d{4}-\d{2}-\d{2} @ [0-9a-f]{40} -->\s*$` **or** the template-placeholder regex `^<!-- reviewed: YYYY-MM-DD @ <hash> -->\s*$`. Marker-shaped text inside fenced code blocks or indented prose is ignored. The placeholder is the divider written by `dev-plan/template.md` for new plans — on first review it must be treated as the divider so `## Progress` / `## Findings` end up below the new marker rather than inside the hashed contract.
3. Split the plan into `(above_marker, below_marker)` at that line. If no marker line of either form is found, treat the whole plan as `above_marker` and `below_marker` as empty.
4. Compute `git hash-object --stdin` of `above_marker`.
5. Compose the new marker line with today's date and the computed hash.
6. Write the plan back: `above_marker` + new marker + a single blank line + `below_marker` (preserved verbatim, so workspace content survives re-review). If `below_marker` was empty, just append the marker as the final line with a trailing newline.

`/review-plan` validates by checking that no placeholder string remains anywhere in the file after the write. If one does, the divider was missed and the workspace is now inside the contract — abort and surface the error.

The marker is idempotent: replacing an existing marker on otherwise unchanged content produces the same hash. Workspace content below the marker is never rehashed, so workspace edits during a `/conduct` run do not require re-review.

## Constraints

- Do not modify the plan *body* automatically — findings drive a conversation, not edits. The trailing review marker footer is the only permitted automated write, and only after explicit user acceptance (`yes`/`waive`).
- The subagent must not receive parent conversation context — fresh eyes are the entire value
- Use model `opus` for the subagent — the quality of analysis justifies the cost
- This skill blocks — the user waits for the review before proceeding
- If the plan references external systems (APIs, services, databases), note that the subagent can only verify what's in the codebase, not external availability
