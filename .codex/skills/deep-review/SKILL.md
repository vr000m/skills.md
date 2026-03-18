---
name: deep-review
description: "Run a multi-lens code review with fresh Codex subagents and strict triage/suppression rules. Use after implementation or when a plan's Review Focus needs targeted review."
argument-hint: "[path/to/plan.md | --pr NUMBER | --full | --continue]"
---

# Deep Review: Multi-Lens Code Review

Run a coordinated review of code changes using fresh Codex subagents. Each lens gets a narrow
prompt, a clean context, and only the target material it needs. Do not pass parent conversation
history into the lens prompts.

## What This Skill Reviews

- A plan file, when you want to use `## Review Focus` as the review brief
- A PR number or URL, when you want to review a pull request diff directly
- The current branch diff, when no explicit input is provided

## Input Resolution

1. If the first argument is a readable plan file path, load it as the review brief and use its
   `## Review Focus` section to steer lens prompts.
2. If the first argument is `--pr` with a number, or a PR URL/number directly, review that PR's
   diff.
3. If the first argument is `--continue` or `--full`, review the current branch diff.
4. If no explicit argument is provided, review the current branch diff against the merge base with
   the default branch.
5. If no target can be resolved, ask the user for a plan path or PR reference.

If a plan file is supplied, treat it as the author-supplied review brief. If the plan's branch does
not match the current branch or the requested PR, call out the mismatch before proceeding.

## Review Focus

If the chosen plan includes `## Review Focus`, use it to:

- Decide whether the spec-compliance lens should run
- Highlight the exact areas that deserve extra scrutiny
- Avoid guessing about standards, backward compatibility, or risk areas the author already named

If there is no plan or no `Review Focus` section, run the non-spec lenses only and skip spec
compliance unless the user explicitly supplies spec/RFC references in the prompt.

## Lens Model Map

Use Codex-native model names and keep the mapping tiered by analysis depth. If a requested model is
unavailable, use the closest supported Codex model in the same reasoning tier.

| Lens | Default model | Why |
|------|---------------|-----|
| Logic | `gpt-5.4` | Deep reasoning for edge cases, state transitions, and failure paths |
| Security | `gpt-5.4` | High-impact findings deserve the strongest analysis available |
| Spec compliance | `gpt-5.4` | Cross-referencing standards requires careful reading |
| Architecture | `gpt-5.4-mini` | Pattern and compatibility analysis with lighter reasoning cost |
| Documentation | `gpt-5.4-mini` | Mostly mechanical drift detection across docs and plans |

## Lens Prompts

Each lens prompt must be self-contained. Give the subagent only the target material, the relevant
`Review Focus`, the repo-root `AGENTS.md` checklist if present, and the lens-specific instructions
below.

### Logic Lens

Look for:
- Off-by-one errors
- State transition bugs
- Error handling gaps
- Race conditions
- Resource lifecycle mistakes
- Dead branches or impossible paths

Ignore:
- Pure style issues
- Naming preferences unless they hide a bug

### Security Lens

Look for:
- Input validation
- Secrets exposure
- Auth/authz mistakes
- Injection risks
- Unsafe filesystem or process interactions
- Data leaks in logs or error paths

Ignore:
- General code style unless it creates a security risk

### Spec Compliance Lens

Only run this lens when the plan's `Review Focus` includes explicit spec or RFC references, or the
user directly asks for standards compliance.

Look for:
- MUST/SHOULD/MAY mismatches
- Missing required steps from the referenced standard
- Ambiguous implementation choices that violate the referenced spec

Ignore:
- Non-spec architectural preferences

### Architecture Lens

Look for:
- Coupling and layering problems
- Backward compatibility regressions
- Public API surface changes
- Naming or module boundaries that will create maintenance churn

Ignore:
- Micro-optimizations
- Style nits

### Documentation Lens

Look for:
- README drift
- AGENTS.md drift
- Dev-plan drift
- Missing command or workflow documentation
- Stale examples or outdated references

Ignore:
- Code behavior unless the docs misstate it

## Orchestration

1. Resolve the target diff and any matching plan brief.
2. Read repo-root `AGENTS.md` if it exists and load the `## Review Checklist` section if present.
3. Show a cost confirmation before spawning lenses. Include the lens list, model mapping, and any
   skipped lenses.
4. Spawn all enabled lens subagents with clean context. Use `spawn_agent` semantics, not worktrees
   or CLI-level process fan-out.
5. Wait for every lens to finish, then consolidate and deduplicate findings.

## Persisted Run State

Store the last run in `.deep-review/latest.json` so `--continue` can rerun only failed lenses.

Suggested schema:
```json
{
  "run_id": "2026-03-17T14:30:00Z",
  "target_kind": "plan|pr|branch",
  "target_ref": "feature/deep-review",
  "base_commit": "abc1234",
  "head_commit": "def5678",
  "diff_hash": "sha256:...",
  "review_focus_source": "docs/dev_plans/20260317-feature-deep-review.md",
  "lenses": {
    "logic": { "status": "completed", "model": "gpt-5.4", "findings": [] },
    "security": { "status": "timed_out", "model": "gpt-5.4", "findings": [] },
    "spec": { "status": "skipped", "reason": "no specs in Review Focus" },
    "architecture": { "status": "completed", "model": "gpt-5.4-mini", "findings": [] },
    "documentation": { "status": "completed", "model": "gpt-5.4-mini", "findings": [] }
  }
}
```

`--continue` rules:
- If the state file is missing, fall back to `--full`
- If `base_commit`, `head_commit`, or `diff_hash` no longer match the current target, warn and fall
  back to `--full`
- If the snapshot matches, rerun only `timed_out` or `errored` lenses and merge them with the saved
  findings
- `--full` always overwrites the state file

If the target comes from a plan file, keep the plan path in `review_focus_source` or an equivalent
field so stale review focus is obvious to the next run.

## Findings Format

Every lens must return structured findings with:
- `severity`: `Critical`, `Important`, or `Minor`
- `category`: `Logic`, `Security`, `Spec`, `Architecture`, or `Documentation`
- `file:line`
- `evidence`
- `suggestion`

When multiple lenses flag the same file:line, keep the higher-severity finding and note the overlap
in the consolidated report.

## Suppression Rules

Read repo-root `AGENTS.md` if present. If it has a `## Review Checklist` section, suppress previously
dismissed patterns using the strict bullet format below:

```markdown
## Review Checklist
- **[Security] won't-fix**: raw SQL in migration scripts is intentional (2026-03-17)
- **[Architecture] analysis-error**: singleton in transport.py is by design, not coupling (2026-03-17)
```

Matching rules:
- Match by category and disposition first
- Compare the normalized description against the finding text
- Do not suppress if the match is too vague or the checklist entry is stale

If repo-root `AGENTS.md` or the `## Review Checklist` section is missing, continue without
suppression.

## Triage

Present one consolidated markdown report to the main context:
- Group findings by severity, highest first
- Note which lenses overlapped on each finding
- Call out which lenses were skipped, timed out, or rerun

When the user marks a finding as `won't-fix` or `analysis-error`, append a new checklist entry to the
repo-root `AGENTS.md` in the strict machine-parseable format above, unless the user explicitly says
not to.

## Cost Confirmation

Show this before spawning lenses, with the actual models that will run:

```text
Deep review will run 4 lenses:
  Logic (gpt-5.4), Security (gpt-5.4), Architecture (gpt-5.4-mini), Documentation (gpt-5.4-mini)
  Spec compliance: skipped (no specs in Review Focus)
Proceed? [Y/n]
```

If the user declines, stop without running any lenses.

## Output

The consolidated report should include:

```markdown
## Deep Review: [target]

**Overall**: [one-line summary]

### Critical
- **[Category]**: [Finding]
  - Evidence: [what was found]
  - Suggestion: [what to change]

### Important
- ...

### Minor
- ...

---
**Next steps**: Review these findings and decide which ones to apply. Update the plan or code with
the accepted changes, then rerun `/deep-review` if the snapshot changed.
```

If the review is clean, say so concisely and note any residual risks or lenses that were skipped.
