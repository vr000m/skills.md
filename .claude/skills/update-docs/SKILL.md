---
name: update-docs
description: Sync project documentation with code changes on the current branch. Checks dev plans, changelogs, READMEs, AGENTS.md, and PR descriptions for staleness against the actual diff, then offers to update them. Use after finishing implementation work, before creating or merging a PR.
argument-hint: [--apply] [--pr NUMBER]
---

# Update Docs Skill

Detect stale documentation and update it to match the current branch's code changes.

## Usage

- `/update-docs` - Audit docs, show what's stale, offer to fix
- `/update-docs --apply` - Audit and apply all updates without prompting
- `/update-docs --pr 42` - Also update the PR description for PR #42

## When to Use

Run this after finishing implementation work on a feature branch, before creating or merging a PR. It catches the docs we routinely forget:
- Dev plan checkboxes left unchecked
- Changelog missing the new version entry
- README not reflecting new commands, config, or architecture changes
- PR description that doesn't match the final state of the work

## Phase 1: Gather Context

1. **Detect the base branch and diff:**
   ```
   # Detect base branch
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
   # Fallback: check if main or master exists
   if [ -z "$BASE" ]; then
     git show-ref --verify --quiet refs/heads/main && BASE=main || BASE=master
   fi

   CURRENT=$(git branch --show-current)
   ```

   **If on a feature branch** (CURRENT != BASE):
   ```
   git log --oneline --no-merges $BASE...HEAD
   git diff $BASE...HEAD --stat
   git diff $BASE...HEAD
   ```
   If the branch has no commits ahead of base, stop early: "Nothing to document — branch is up to date with {base}."

   **If on the base branch itself** (CURRENT == BASE):
   Use the most recent commits since the last doc-touching commit as the diff range:
   ```
   # Find last commit that touched docs
   LAST_DOC_COMMIT=$(git log --oneline --diff-filter=M -- '*.md' -1 --format='%H')
   # If no doc commits exist, use the last 5 commits
   RANGE="${LAST_DOC_COMMIT:-HEAD~5}..HEAD"
   git log --oneline --no-merges $RANGE
   git diff $RANGE --stat
   git diff $RANGE
   ```
   Warn the user: "You're on {base} directly. Auditing the last N commits for doc staleness."

2. **Identify the change summary:**
   - Files added, modified, deleted
   - New CLI commands, flags, or config options
   - New/changed public APIs (classes, methods, functions)
   - New dependencies
   - Test files added or modified

3. **Discover documentation files in the project:**
   Scan for these (all optional — skip any that don't exist):
   - `docs/dev_plans/*.md` — development plans
   - `CHANGELOG.md` — changelog
   - `README.md` or `docs/README.md` — project README
   - `CLAUDE.md` — Claude Code project instructions
   - `AGENTS.md` — Codex/agent instructions
   - Active PR description (if `--pr` flag or branch has an open PR)

## Phase 2: Audit Each Document

For each discovered document, compare its content against the branch diff and produce findings.

### Dev Plans (`docs/dev_plans/*.md`)

Look for the plan most relevant to the current branch (match by branch name in header, or by recency).

Check:
- [ ] **Status header** — should it be updated? (e.g., "In Progress" to "Complete", version bumped)
- [ ] **Unchecked boxes** — are there checklist items that the diff shows are now done?
- [ ] **Missing items** — did the implementation add work not in the plan? (new files, phases, or decisions)
- [ ] **Stale references** — do file paths, method names, or config keys in the plan match the code?

### Changelog (`CHANGELOG.md`)

Check:
- [ ] **Missing version section** — if the branch introduces a version bump (check `pyproject.toml`, `package.json`, `Cargo.toml`, `version.py`, etc.), is there a corresponding `## [x.y.z]` section?
- [ ] **Undocumented changes** — are there Added/Changed/Fixed/Removed items from the diff not reflected in the changelog?
- [ ] **Format consistency** — does the new entry follow the same style as existing entries (Keep a Changelog, bullet style, etc.)?

### README (`README.md` or `docs/README.md`)

Check:
- [ ] **New commands/flags** — if the diff adds CLI commands or flags, are they documented?
- [ ] **Architecture changes** — if the diff adds new modules, services, or significant components, does the architecture section reflect them?
- [ ] **Project structure** — if the diff adds new directories or files mentioned in a project structure tree, is the tree updated?
- [ ] **Setup/install changes** — if dependencies changed, are install instructions still correct?
- [ ] **New tools/APIs** — if new MCP tools, API endpoints, or public interfaces were added, are they listed?

### CLAUDE.md

Check:
- [ ] **New commands** — if the diff adds CLI commands or dev workflow commands, are they in the Commands section?
- [ ] **Versioning** — if version locations changed, is the Versioning section updated?
- [ ] **Project layout** — if new directories or key files were added, is the layout tree updated?

### AGENTS.md

Check:
- [ ] **New commands** — if the diff adds CLI commands, build steps, or dev workflow commands, are they documented?
- [ ] **Project layout** — if new directories or key files were added, is the layout tree updated?
- [ ] **Tool/API changes** — if new tools, endpoints, or public interfaces were added, are they listed?

### PR Description

Only checked if `--pr NUMBER` is provided or the branch has an open PR. Detect via:
```
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
```
If `gh` is not installed or not authenticated, skip PR checks and note it in the report.

Check:
- [ ] **Summary** — does the PR summary accurately describe all commits on the branch?
- [ ] **Test plan** — does the PR mention how changes were tested?
- [ ] **Completeness** — are all significant changes mentioned (not just the last commit)?

## Phase 3: Report Findings

Present a structured report:

```
## Documentation Audit

**Branch:** feature/my-feature (12 commits ahead of main)
**Files changed:** 15 files (+420, -89)

### Dev Plan: docs/dev_plans/20260218-feature-foo.md
- [ ] Update status from "In Progress (v0.0.6)" to "In Progress (v0.0.7)"
- [ ] Check boxes: Phase 6 items 1-3 (implemented in this branch)
- [ ] Add: new `delete_by_repo()` method not in original plan

### CHANGELOG.md
- [ ] Add [0.0.7] section with:
  - Added: incremental refresh with `--force` flag
  - Added: symbol lookup filter cascade (class_name -> method_name -> fallback)
  - Added: `delete_by_repo()` for per-repo index cleanup
  - Changed: `refresh` skips unchanged sources (docs hash + repo SHA tracking)
  - Fixed: docs hash not persisted after errored ingest

### README.md (docs/README.md)
- (up to date, no changes needed)

### CLAUDE.md
- (up to date, no changes needed)
```

## Phase 4: Apply Updates

If `--apply` was passed, or the user confirms, apply the updates. **Always show the report (Phase 3) first**, even in `--apply` mode, so the user sees what will change.

1. Edit each document using the Edit tool (prefer surgical edits over full rewrites)
2. For dev plans: check boxes, update status, add missing items
3. For changelog: insert the new version section following existing format exactly
4. For README: add missing sections/entries where appropriate
5. For CLAUDE.md: update commands, layout, or versioning sections
6. For AGENTS.md: update commands, layout, or tool/API sections
7. For PR description: use `gh pr edit --body` to update
8. **Verify each edit**: re-read the modified file after editing to confirm the change landed correctly

After applying, show a summary:
```
Updated 3 files:
  - docs/dev_plans/20260218-feature-foo.md (status + 4 checkboxes + 1 new item)
  - CHANGELOG.md (added [0.0.7] section)
  - PR #11 description (updated summary + test plan)
```

**Do NOT create new documentation files.** Only update existing ones. If a project has no CHANGELOG.md, don't create one — just note it in the report.

## Phase 5: Offer Next Steps

After the report (or after applying), offer:
1. "Apply all updates" (if not already applied)
2. "Stage and commit the doc updates"
3. "Show me the diff of what changed"

Only commit if the user explicitly asks. Use a commit message like:
```
docs: sync documentation with $(git branch --show-current) changes
```

## Edge Cases

- **No docs found**: Report "No documentation files found in this project. Consider adding a CHANGELOG.md or README.md."
- **Monorepo**: If multiple `CHANGELOG.md` or `README.md` files exist, audit the ones closest to the changed files.
- **No version bump detected**: Skip the "missing version section" changelog check. Still check for undocumented changes.
- **Merge commits**: Use `git log --no-merges` to focus on actual work commits.
- **Draft PR**: Still audit the PR description — drafts need docs too.
- **On main/master directly**: Still useful — audits recent commits for doc staleness. Uses the range since the last doc-touching commit as the comparison window.
