# Codex Mirror Backlog

Purpose: track known Claude/Codex skill drift after a Claude-side change lands before the Codex analogue is adapted. Use this file when parity is intentionally deferred so the debt is visible beyond a transient handoff note.

## How to Add Entries

When a Claude skill change has no Codex equivalent yet, append an entry with:

- Date and source PR/commit.
- Claude files changed.
- Codex files needing analogous updates.
- Whether the required result is byte-identical parity or Codex-native adaptation.
- Gating checks the Codex maintainer must clear.

Do not list ordinary harness-specific wording as drift. `SKILL.md` files may legitimately differ where Claude uses Agent/subagent wording and Codex uses `spawn_agent`, Codex model names, or Codex state-file names. Rubrics that declare parity must remain byte-identical.

## Current State

As of 2026-05-06, the PR #16 Codex mirror is adapted and parity-clean:

- Source merge: `222644a` (`Merge pull request #16 from vr000m/feature/skill-improvements-from-usage-report`).
- Source commits mirrored/adapted: `c318c2f`, `5e8f6ac`, `4131fd9`, `bbf3c1a`, `a082d4b`.
- Codex files adapted:
  - `.codex/skills/deep-review/SKILL.md`
  - `.codex/skills/deep-review/rubric.md`
  - `.codex/skills/dev-plan/SKILL.md`
  - `.codex/skills/dev-plan/rubric.md`
  - `.codex/skills/update-docs/SKILL.md`
- Gating checks:
  - `just check-prompt-parity`
  - `just check-trunk-snippet-parity`

No open Codex mirror backlog entries are known at this point.
