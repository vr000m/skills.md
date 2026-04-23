---
name: review-plan
description: "Review a development plan for gaps, undocumented assumptions, missing constraints, and architectural risks before implementation begins. Use this skill after a dev-plan is created, when the user says \"review plan\", \"audit plan\", \"check plan\", or \"/review-plan\". Also trigger proactively whenever a dev-plan skill completes and produces a plan file - catching gaps before coding starts is far cheaper than discovering them mid-implementation."
argument-hint: "[path/to/plan.md]"
---

# Review Plan: Independent Plan Audit

Audit a development plan before implementation begins. Read the plan as if you were not part of the conversation that produced it - that fresh-reader posture is the point. Verify the written plan against the codebase instead of relying on unstated context from the parent conversation.

## Why This Exists

Plans encode assumptions. Some are stated, most are not. The author knows what they meant; a fresh reader sees only what is written. This skill exploits that gap: review the plan cold, explore the codebase to verify claims, and surface what is missing, ambiguous, or risky. Findings go back to the user for discussion - the plan body is never modified automatically. The sole exception is the trailing review marker footer written after the user explicitly accepts or waives the findings; `/conduct` consumes that marker as its readiness signal.

## When to Run

- **After `/dev-plan create`** - this is the primary trigger. Run automatically, blocking, before implementation starts.
- **Manually via `/review-plan [path]`** - when the user wants to audit a plan mid-cycle or re-check after updates.
- **Before `/fan-out`** - if a plan has not been reviewed yet, catch gaps before parallelizing work across agents.

## Path Resolution

1. If a path argument is provided, use it directly
2. If no path is provided, scan `docs/dev_plans/` for the most recent plan file by modification time. Match the naming convention `YYYYMMDD-type-name.md` and exclude helper files such as `README.md`
3. If triggered right after `/dev-plan`, the plan path is already in conversation context - use it
4. If no plan is found, tell the user and ask for a path

## Execution

### Step 1: Read the Plan

Read the full plan file. Extract:
- The objective and requirements
- The implementation checklist (phases, tasks)
- Technical specifications (files to modify, interfaces, architecture decisions)
- Integration seams (if present)
- Acceptance criteria
- Review Focus (if present)
- Any stated constraints

### Step 2: Audit the Plan

Run the audit in the current Codex session. Do not require `spawn_agent`; this skill must work in ordinary `/review-plan` runs where delegation has not been explicitly requested.

Use this audit checklist:

1. **Read the plan carefully.** Understand the objective, requirements, tasks, and technical specs.
   If the plan has a `## Review Focus` section, treat it as explicit review scope and verify that any
   listed specs, RFCs, or risk areas are concrete enough for downstream review tooling to use.
2. **Explore the codebase.** Validate every assumption the plan makes:
   - Do the files listed in "Files to Modify" actually exist? Are the paths correct?
   - Do the APIs, functions, classes, or patterns referenced in the plan exist in the codebase?
   - Does the project structure match what the plan assumes?
   - Are the dependencies the plan relies on actually available?
   - Check `package.json`, `pyproject.toml`, `Cargo.toml`, and similar project files for dependency versions
3. **Identify gaps.** Look for:
   - **Undocumented assumptions** - things the plan takes for granted but does not state
   - **Missing constraints** - limits, edge cases, or failure modes not addressed
   - **Ambiguous requirements** - statements that could be interpreted multiple ways
   - **Architectural risks** - patterns that conflict with the existing codebase, scaling concerns, or coupling issues
   - **Sequencing problems** - tasks ordered wrong, or dependencies between "independent" tasks
   - **Missing tasks** - work that is clearly needed but not listed (for example migrations, config changes, or docs)
   - **Testing gaps** - scenarios not covered by the testing plan
   - **Integration seam risks** - boundaries where independently-built pieces must connect
4. **Produce findings.** For each issue found, provide:
   - **Category**: one of [Assumption, Constraint, Ambiguity, Risk, Sequencing, Missing Task, Testing Gap]
   - **Severity**: Critical (blocks implementation), Important (likely causes rework), Minor (nice to address)
   - **Finding**: What the issue is
   - **Evidence**: What you found in the codebase that supports this finding
   - **Suggestion**: A specific constraint, clarification, or task to add to the plan

Treat the review as a cold read:
- Base the audit on the plan text and what you verify in the repository
- Do not rely on unstated details from the parent conversation
- If the user explicitly asks for delegated review and the environment supports it, delegation is optional, not required. Use a supported high-reasoning Codex model from the current environment (for example `o3`) instead of hardcoding a stale model ID

### Step 3: Present Findings

Present the findings to the user. Format them clearly:

```markdown
## Plan Review: [plan-file-name]

**Overall**: [one-line summary of plan quality]

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

Do NOT modify the plan body automatically. The findings are a starting point for conversation:
- The user may accept some findings and reject others
- Some findings may need clarification or deeper investigation
- Accepted findings should be incorporated via `/dev-plan update`

Only after the user has reviewed and addressed the findings (or explicitly decided to proceed) should implementation begin.

### Step 5: Write the Review Marker

After findings have been presented and discussed, ask the user one question:

> Are findings addressed? (`yes` / `waive` / `no`)

- `yes` — the user incorporated the findings they intend to address. Write the marker.
- `waive` — the user reviewed the findings and chose not to act on them. Write the marker anyway.
- `no` — exit without writing. The user can rerun `/review-plan` later.

The review marker is a single HTML-comment line appended as the final line of the plan file:

```html
<!-- reviewed: YYYY-MM-DD @ <hash> -->
```

- `YYYY-MM-DD` is today's date.
- `<hash>` is the 40-character SHA-1 from `git hash-object <tmpfile>`, where `<tmpfile>` is the plan with its final line removed only if that final line already matches `^<!-- reviewed: \d{4}-\d{2}-\d{2} @ [0-9a-f]{40} -->\s*$`. Otherwise hash the plan as-is.

Procedure:

1. Read the plan file.
2. If the final non-empty line matches the marker regex, strip only that final line in memory; marker-shaped text elsewhere in the body stays untouched.
3. Compute `git hash-object` of the stripped content.
4. Append or replace the trailing marker so it is the final line of the file, with exactly one trailing newline.

Only the final non-empty line counts as the review marker. Marker-shaped text inside prose or code fences is ignored by both the hashing step here and `/conduct` preflight later.

## Constraints

- Never modify the plan body automatically - findings drive a conversation, not automatic edits. The trailing review marker footer is the only allowed automated write, and only after explicit user acceptance (`yes`/`waive`).
- Review from the plan text and the codebase, not from unstated parent-conversation context
- If you delegate, use a supported high-reasoning Codex model from the current environment instead of hardcoding a specific model ID in the skill
- This skill blocks - the user waits for the review before proceeding
- If the plan references external systems (APIs, services, databases), note that the review can only verify what is in the codebase, not external availability
