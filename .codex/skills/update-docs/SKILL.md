---
name: update-docs
description: Syncs project documentation with code changes on the current branch by checking dev plans, changelogs, READMEs, AGENTS.md, and PR descriptions for staleness against the actual diff, then offering targeted updates. Use after finishing implementation work, before creating or merging a PR, or when the user says "update docs" or "/update-docs".
argument-hint: "[--apply] [--pr NUMBER]"
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

## Phases 1–3: Gather Context, Audit Documents, Report Findings

These phases involve heavy git diffs, file reads, and cross-referencing. If subagent delegation is available and explicitly allowed in the current Codex runtime, you may delegate them to keep the main context lean. Otherwise, run the same steps in the main context so the skill still works without delegation.

If delegation is available and explicitly allowed, use `spawn_agent` with a Codex model such as `gpt-5.4-mini` to run the following self-contained prompt (fill in the `{{PLACEHOLDERS}}`). If delegation is unavailable, use the same prompt contract in the main context instead.

````
You are auditing project documentation for staleness against the current branch's code changes.

## Inputs

- **Current branch**: {{CURRENT_BRANCH}}
- **Base branch**: {{BASE_BRANCH}}
- **PR number** (if any): {{PR_NUMBER or "none"}}
- **Arguments**: {{RAW_ARGS}}

## Phase 1: Gather Context

1. **Detect the diff range:**

   **If on a feature branch** (current != base):
   ```
   MERGE_BASE=$(git merge-base "{{BASE_BRANCH}}" HEAD)
   git log --oneline --no-merges "$MERGE_BASE..HEAD"
   git diff "$MERGE_BASE..HEAD" --stat
   git diff "$MERGE_BASE..HEAD"
   ```
   If `git rev-list --count "$MERGE_BASE..HEAD"` is `0`, return: "Nothing to document — branch is up to date with {{BASE_BRANCH}}."

   **If on the base branch itself**:
   Use the most recent commits since the last doc-touching commit as the diff range:
   ```
   LAST_DOC_COMMIT=$(git log --diff-filter=AMR --format='%H' -1 -- '*.md' 'docs/**')
   RANGE="${LAST_DOC_COMMIT:-HEAD~5}..HEAD"
   git log --oneline --no-merges $RANGE
   git diff $RANGE --stat
   git diff $RANGE
   ```

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
   - Active PR description (if PR number provided or branch has an open PR)

## Phase 2: Audit Each Document

For each discovered document, compare its content against the branch diff and produce findings.

### Dev Plans (`docs/dev_plans/*.md`)
Look for the plan most relevant to the current branch (match by branch name in header, or by recency).
Check:
- [ ] **Status header** — should it be updated? (e.g., "In Progress" to "Complete", version bumped)
- [ ] **Unchecked boxes** — are there checklist items that the diff shows are now done?
- [ ] **Missing items** — did the implementation add work not in the plan? (new files, phases, or decisions)
- [ ] **Stale references** — do file paths, method names, or config keys in the plan match the code?
- [ ] **Stale descriptions** — do technical-spec tables, authority decisions, and prose summaries still accurately describe what each file does in the current diff? Re-read each row/statement against the actual code, not just the path.

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
- [ ] **Skill triggers and routing** — if skills were added/renamed/removed, does `AGENTS.md` reflect accurate trigger rules and skill paths?
- [ ] **Codex instruction sections** — if execution norms changed, are sections like editing constraints, formatting rules, and collaboration mode still accurate?
- [ ] **Tooling assumptions** — if commands were changed (e.g., `rg` vs alternatives, test/lint commands), does `AGENTS.md` still describe the preferred tools and fallbacks?
- [ ] **Cross-agent consistency** — if both `AGENTS.md` and `CLAUDE.md` exist, do shared command examples and project-layout statements agree?

### PR Description
Only checked if a PR number is provided or the branch has an open PR. Detect via:
```
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
```
Graceful fallback:
```
PR_NUMBER=$(gh pr list --head "$(git branch --show-current)" --json number,isDraft -q '.[0].number' 2>/dev/null)
```
If `gh` is not installed or not authenticated, skip PR checks and note it in the report.
Check:
- [ ] **Summary** — does the PR summary accurately describe all commits on the branch?
- [ ] **Test plan** — does the PR mention how changes were tested?
- [ ] **Completeness** — are all significant changes mentioned (not just the last commit)?

## Phase 3: Return Structured Report

Return your findings in exactly this format (no other output):

```
## Documentation Audit

**Branch:** <branch> (<N> commits ahead of <base>)
**Files changed:** <N> files (+X, -Y)

### <Doc path>
- [ ] <finding 1>
- [ ] <finding 2>

### <Doc path>
- (up to date, no changes needed)
```

Include every discovered doc file in the report, even if it's up to date.
````

### Pre-flight (main context)

Before spawning the subagent, the main context must:

1. Detect the base branch:
   ```
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
   if [ -z "$BASE" ]; then
     if git show-ref --verify --quiet refs/heads/main; then BASE=main
     elif git show-ref --verify --quiet refs/heads/master; then BASE=master
     else BASE=$(git for-each-ref --format='%(refname:short)' refs/heads | head -n 1); fi
   fi
   CURRENT=$(git branch --show-current)
   ```
2. Detect PR number (if `--pr` flag or branch has an open PR).
3. Fill in the placeholders and spawn the subagent.
4. If you delegated, present the subagent's structured report to the user. If you ran Phases 1-3 locally, present the structured report directly.

## Phase 4: Apply Updates

If `--apply` was passed, or the user confirms, apply the updates. **Always show the report (Phase 3) first**, even in `--apply` mode, so the user sees what will change.

1. Edit each document directly (prefer surgical edits over full rewrites)
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
- **Committing on base branch**: If there are direct commits on `main`/`master`, avoid broad history rewrites; only propose doc updates for the computed audit range.
