---
name: conduct
description: Walks a reviewed dev-plan phase by phase and delegates each phase's implementation, testing, and fix loop to clean-context subagents. Main Claude stays in a conductor role so context does not exhaust during multi-phase execution. Use when the user says "step through plan", "walk phases", "delegate phase implementation", "conduct plan", "run the plan", or invokes this skill directly with a dev-plan path.
argument-hint: "[path/to/plan.md] [--resume] [--status] [--pause-phase] [--abort-run] [--test-cmd CMD] [--test-timeout SECS] [--max-iterations N]"
---

# Conduct: Phased Delegation for Linear Implementation

Walk a reviewed dev-plan phase by phase. For each phase, spawn clean-context subagents (implementer + test-writer, and optionally a lightweight reviewer) to do the work. The conductor — main Claude running this skill — only reads structured JSON reports, routes failures through a bounded fix loop, commits at phase boundaries, and hands back to the user between phases.

This file is a scaffold. Detailed workflow (preflight, per-phase steps, fix loop, commit strategy, handback, CLI flags, state file, lockfile) lands in subsequent phases of the feature branch. Subagent prompt templates live alongside this file:

- `implementer-prompt.md`
- `test-writer-prompt.md`
- `reviewer-prompt.md`

## Delegation Pattern

Delegation depth from this skill is exactly 1: skill → workers. Workers never spawn further subagents. This skill is invoked directly by the user as a top-level skill, OR inside a subprocess spawned by a parallelising skill that re-baselines depth at the process boundary. It is never invoked as an Agent subagent.

## When to Run

Run on a dev-plan that has been reviewed and carries the trailing review-marker footer written by the review-plan skill after user acceptance. Without that marker, the skill hard-stops at preflight.

## Invocation

```
conduct <plan-path>
conduct --resume <plan-path>
conduct --status <plan-path>
conduct --pause-phase <plan-path>
conduct --abort-run <plan-path>
```

- `--pause-phase` stashes uncommitted work and keeps state so work can be resumed later.
- `--abort-run` discards state entirely; the more-destructive flag has the more-explicit name.

## Implementation Status

This scaffold ships the skill directory and prompt templates. Workflow logic, state file handling, and the lockfile are filled in by later phases in the feature branch that introduces this skill.
