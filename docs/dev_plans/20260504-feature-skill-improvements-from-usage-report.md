# Task: Skill improvements driven by usage-report friction patterns

**Status**: Not Started
**Assigned to**: Claude Code
**Priority**: Medium
**Branch**: feature/skill-improvements-from-usage-report
**Created**: 2026-05-04
**Completed**:

## Objective

Land three targeted skill-level fixes that address remaining friction patterns surfaced in `~/.claude/usage-data/report.html` (3,361 messages / 163 sessions, 2026-03-10 to 2026-05-03). Each fix is a small, additive edit to an existing `SKILL.md` — no new skills, no new infrastructure.

## Context

The report identified three classes of friction. Two have already landed:

- Harness-level fixes: PostToolUse formatter hook, PreToolUse `git add -A` block.
- Behavioral fixes: CLAUDE.md sections on Commit Hygiene, Pre-Push Checks, Review Workflow, Plan Updates, Auto-Memory Hygiene.

A third class — the `conduct` marker invalidating on workspace edits — was already fixed in commit `59daefc` (2026-05-01) "feat(plans): split plan into contract above marker / workspace below". `## Progress` and `## Findings` are now below the marker so checkbox toggles and findings appends no longer invalidate the contract hash. **No further conduct work is in scope for this plan.**

The remaining items need to be enforced **inside the skills** so the rules trigger automatically when the relevant skill runs:

1. **`deep-review`** — diff-scope and **worktree-identity** confirmation. Two distinct failure modes:
   - **Diff-scope**: worktree diff vs branch diff vs PR diff confused; banner never echoes resolved range.
   - **Worktree-identity**: when multiple Claude sessions share a repo via separate `git worktree`s, the harness state can lose track of which worktree's branch is current. After a commit lands, the next invocation may resolve `<base>..<head>` against a sibling worktree's branch instead of the active one. The fix anchors branch identity on `git rev-parse --show-toplevel` + `git branch --show-current` *from inside the worktree at every invocation*, ignoring any cached harness branch state, and surfaces concurrent worktrees as informational context.
2. **`dev-plan`** — Explore freshness for git-ref references (tags, branches, commits) — point-in-time at create only.
3. **`update-docs`** — sibling-plan auto-detection. Extend the existing dev-plan audit pass with slug + component matching; explicitly scope the audit to `docs/dev_plans/` and exclude `tests/fixtures/`.

The three fixes are independent; they ship in one PR, one commit per skill. No dispatch contracts change.

**Mirror parity:** All three skills have `.codex/skills/` mirrors. Per memory `feedback_no_codex_edits.md`, never edit `.codex/skills/` directly. The Codex maintainer mirrors separately. Adding the 5th Explore category modifies the byte-identical `<!-- BEGIN GENERIC EXPLORE PROMPT -->` block in `dev-plan/SKILL.md`; **byte-identity across `.claude/` and `.codex/` is intentionally broken until Codex maintainer mirrors** (`[CODEX-DEFERRED]`). `just check-sync` verifies repo-vs-global only, not cross-harness byte-identity.

**Workflow direction note (important).** This repo's edit flow is: edit `.claude/skills/<x>/SKILL.md` in the repo → review → merge → run `just promote-skills` (repo → global). Pre-merge, repo and `~/.claude/skills/` will intentionally differ; `just check-sync` will flag this expected drift. **`just sync-skills` (global → repo) is the WRONG direction for this PR's workflow** and is not invoked in any phase. Behavioral verification (running the new code) happens only post-merge after `just promote-skills` has propagated the edits to global.

## Scope tags

- **[GENERIC]** — applies to both harnesses; should land byte-identically in `.claude/` and `.codex/` once Codex mirrors.
- **[CLAUDE]** — Claude-specific phrasing (Agent tool, model slugs).
- **[CODEX-DEFERRED]** — Codex maintainer follow-up; out of scope for this PR.

## Requirements

### 1. `deep-review` — diff-scope + worktree-identity preflight

- **[GENERIC]** Resolve branch identity *every run* via `git rev-parse --show-toplevel` + `git branch --show-current` from the current working directory. Ignore any cached harness branch state. Worktree-identity is per-invocation, not cached.
- **[GENERIC]** Banner: `Reviewing: <branch> @ <worktree-root> | <base>..<head> (<N> commits, <M> files)`.
  - In **`--continue` resume mode** (HEAD == stored head, state file present and schema-matched), the banner shows the **stored** range with a `(resume)` tag, not the freshly-resolved range, since only errored lenses re-run against stored state.
  - In **`--continue` schema-mismatch / missing-state-file fallback**, behaves as `--full`: fresh-resolved range, no `(resume)` tag, and the existing schema-mismatch warning prints first.
  - In **all other modes** (full / incremental), the banner shows the freshly-resolved range about to be reviewed.
  - For **`--pr <N>` mode**, `<base>..<head>` resolves to `origin/<base-branch>..<pr-head-sha>` (the GitHub PR base and head); banner is the literal grep target for AC.
- **[GENERIC]** When `git worktree list` returns more than one active worktree, append a second informational line to the banner: `Other worktrees present (informational): <count> (<root1>, <root2>); anchored to <root>`. Labelled "informational" not "warning" to avoid training users to ignore it on stale-worktree setups. The list of other worktrees is included in the banner text.
- **[GENERIC]** When invoked without `--pr` or `--continue` and the current branch matches the configured trunk (resolved by `git symbolic-ref refs/remotes/origin/HEAD` if available, falling back to `main`/`master` by name), halt with: `"Refusing to review trunk against itself — pass --pr <N> or check out a feature branch."` The halt fires **before** any `.deep-review/latest-claude.json` write, so a subsequent `--continue` from a feature branch is not poisoned.
- **[GENERIC]** When `--continue` falls back to `--full` mode (force-push, rebase, branch switch), the existing warning has the resolved-range banner appended (separate code path from pre-dispatch banner).
- **[GENERIC]** The model-facing review-state section gets an explicit "Confirm scope before dispatch" gate listing the banner output as the proceed signal.
- **[GENERIC]** **Cache-bypass behavior.** The skill ignores any harness-cached branch state. If the Claude harness exposes no such cache surface, this requirement is documented as a no-op contract ("there is no cache surface to bypass; per-invocation resolution is the only path"). If a cache surface exists, the skill explicitly does not consult it.
- **[GENERIC]** Trunk-resolution snippet (`git symbolic-ref refs/remotes/origin/HEAD` + main/master fallback) currently lives in `update-docs/SKILL.md`; this requirement duplicates it verbatim. SKILL.md files are prose prompts with no include mechanism in this repo, so duplication is the available pattern. Follow-up: if a third skill needs trunk resolution, copy the snippet verbatim from `update-docs/SKILL.md` and add a grep-based parity check in `scripts/` to keep the copies in sync.
- **[GENERIC]** **Rubric update.** `deep-review/rubric.md` exists; append one criterion verbatim: *"Pre-dispatch banner prints resolved range and worktree identity; trunk-vs-trunk halt fires before any state-file write; `--continue` resume mode shows stored range with `(resume)` tag."*

### 2. `dev-plan` — Explore extends to git refs (point-in-time)

- **[GENERIC]** Explore's structured-fact contract gains a fifth category: **verified git refs** (point-in-time). Match references in the user request via `v\d+\.\d+\.\d+`, `origin/<name>`, `<name>@<sha>`. Verify with `git rev-parse --verify`; report `verified` / `unverified` with the same shape as `verified paths`.
- **[GENERIC]** Unverified refs list a reason (`tag not found`, `branch tracks gone-remote`, `sha unknown`).
- **[GENERIC]** **Point-in-time disclaimer (asymmetric to other fact categories).** Verification runs at `dev-plan create` only. A verified ref recorded above the marker is a fact-as-of-create, not a live invariant. `/conduct` does not re-verify; ref drift after create does **not** force re-review (asymmetric to path/pattern/dependency drift, which does). The asymmetry is documented in **one canonical location** — a new "Point-in-time facts" subsection in `dev-plan/SKILL.md` Constraints — referenced (not duplicated) by the rubric line and the prompt body. This avoids scattering the carve-out across three docs.
- **[GENERIC]** Generic-block edit: the new category lives inside the `<!-- BEGIN GENERIC EXPLORE PROMPT -->` markers in `dev-plan/SKILL.md` (lines 107-159). Until Codex mirrors, byte-identity across `.claude/` and `.codex/` is intentionally broken — `[CODEX-DEFERRED]`.
- **[GENERIC]** No change to dispatch.
- **[GENERIC]** **Rubric update.** `dev-plan/rubric.md` gains exactly one new criterion verbatim: *"Git refs (tags, branches, commits) referenced in the request are listed as verified or unverified with point-in-time disclaimer; ref drift after create does not force re-review (asymmetric to paths/patterns/dependencies, which do)."*
- **[GENERIC]** No `dev-plan/template.md` change needed.

### 3. `update-docs` — extend existing dev-plan audit with sibling-slug match

- **[GENERIC]** Extend the existing dev-plan audit pass (matches by branch name in header, or by recency — see the phrase "match by branch name in header, or by recency" in `update-docs/SKILL.md`). Do not add a parallel grep.
- **[GENERIC]** **Audit scope.** The slug-match grep is scoped to `docs/dev_plans/*.md` (or the project's configured plans dir). **Fixture trees under `tests/fixtures/dev_plans/` are excluded by default.** This is mandatory, not optional — Phase 6's self-test depends on it.
- **[GENERIC]** **Slug match rule.** Filename strips the `YYYYMMDD-` date prefix; the **leading type token** (`feature`, `bug`, `chore`, `docs`, `design`, `refactor`) is also stripped — type prefixes are metadata and would otherwise match every plan of the same type. The remaining string is the tokenisation slug. **Tokens are hyphen-delimited segments of that stripped slug; no further stop-word filtering.** Sibling-slug match is exact on the full stripped slug or any contiguous substring of ≥3 tokens within it.
- **[GENERIC]** **Component match rule.** Case-insensitive substring of the **primary plan's `Files to Modify` paths** searched against **sibling plan body text** (direction explicit: primary's paths → sibling's body, not vice versa).
- **[GENERIC]** **Filename-convention fallback.** Hand-named plans without `YYYYMMDD-` prefix fall back to full-filename slug match (basename minus `.md`). Audit logs a one-line note when fallback is used.
- **[GENERIC]** **Files-to-Modify-absent fallback.** When the primary plan has no `Files to Modify` section, component match is skipped; slug match still runs.
- **[GENERIC]** **Surfacing.** Non-blocking: skill prints "candidate sibling plans — also touch?" with matches and proceeds. The literal sentinel string when no siblings are found is `audit: no sibling plans matched` (used by Phase 6 fixture verification).
- **[GENERIC]** **Commit-preamble.** A `skipped: <slug> (<reason>)` line per unselected sibling is appended to the commit-message preamble. When no candidates were surfaced, no audit lines appear in the preamble.
- **[GENERIC]** No grep is run if the invocation isn't tied to a dev plan.
- **[GENERIC]** Worked example included in the SKILL.md edit.

## Review Focus

- **[GENERIC] Mirror parity is out of scope for this PR.** `.codex/skills/` edits are the Codex maintainer's responsibility.
- **[GENERIC] Workflow direction.** This PR uses `just promote-skills` (repo → global) post-merge. **`just sync-skills` is not invoked.** Pre-merge drift between repo and global is intentional.
- **[GENERIC] `just check-sync` semantics.** Compares repo-vs-global only. Pre-merge, expect drift on the three target skills (this is correct). Post-merge after `promote-skills`, expect `ok: deep-review`, `ok: dev-plan`, `ok: update-docs` on Claude side; `skip:` on Codex side.
- **[GENERIC] Additive only.** No dispatch contract changes.
- **[GENERIC] Rubrics.** Both `deep-review/rubric.md` (existing) and `dev-plan/rubric.md` (existing) gain one criterion each — verbatim text in Requirements 1 and 2. `update-docs` does not currently have a rubric; do not introduce one in this PR.
- **[GENERIC] Self-claim updates.** `dev-plan/rubric.md:3` and the GENERIC EXPLORE block header in `dev-plan/SKILL.md` self-declare byte-identical mirroring with `.codex/`. Phases 1 & 2 silently invalidate those claims until Codex mirrors. Update those self-claim lines in the same commits to read "Intended to be mirrored byte-identically — see `CODEX_MIRROR_BACKLOG.md` for current drift." Same convention applied to the `deep-review/rubric.md` header if it carries a similar self-claim.
- **[GENERIC] `check-prompt-parity` will fail mid-PR.** `scripts/check-prompt-parity.sh` enforces byte-identity of `rubric.md` for every MANAGED_SKILLS entry (includes `deep-review` and `dev-plan`). Phase 1 & 2 rubric edits land before Codex mirror, so anyone running `just check-prompt-parity` between merge and Codex-mirror landing gets exit 1. **No pre-merge phase invokes `check-prompt-parity`.** The `CODEX_MIRROR_BACKLOG.md` entry (Phase 6) lists `check-prompt-parity` as a gating check the Codex maintainer must clear when mirroring.
- **[GENERIC] Backward compatibility (refined).** Every skill remains invocable with its existing argument set, **except where new halts intentionally trigger on previously-silent-wrong-output cases** (e.g., `deep-review` on trunk without `--pr`/`--continue`). Such halts are treated as fixes, not regressions.
- **[GENERIC] Behavioral verification is post-merge only.** Pre-merge phases (1-5) cover code edits and code-level review. Phase 6 (post-merge, after `just promote-skills`) runs the dogfood, backward-compat baselines, and self-test.

## Files to Modify

- `.claude/skills/deep-review/SKILL.md` — diff-scope + worktree-identity banner; concurrent-worktree info line; trunk-vs-trunk halt + halt-before-state-write rule; `--continue` resume mode `(resume)` tag; `--continue` fallback banner extension; "Confirm scope before dispatch" step.
- `.claude/skills/deep-review/rubric.md` — append the verbatim criterion in Requirement 1.
- `.claude/skills/dev-plan/SKILL.md` — extend GENERIC EXPLORE PROMPT block with `verified git refs` category + point-in-time disclaimer.
- `.claude/skills/dev-plan/rubric.md` — append the verbatim criterion in Requirement 2.
- `.claude/skills/update-docs/SKILL.md` — extend dev-plan audit with slug + component match rules + fixture-dir exclusion + fallbacks + sentinel string + commit-preamble + worked example.
- `docs/dev_plans/README.md` — task-table entry (added in Phase 0; status flipped in Phase 5).
- `~/.claude/usage-data/report.html` — flip annotated NOT-FIXED → FIXED badges in Phase 6 post-merge.

**Out of scope (Codex maintainer follow-up):** `.codex/skills/{deep-review,dev-plan,update-docs}/SKILL.md` and `.codex/skills/{deep-review,dev-plan}/rubric.md`.

**Verification artifacts.** Phase 6 captures fixture transcripts directly into `## Findings` as inline markdown code blocks. No new fixture files committed to `tests/fixtures/` — keeps the change surface text-only and avoids a separate post-merge fixture-commit PR.

## Phases

### Phase 0: Pre-flight
- [ ] Confirm this `/review-plan` round wrote the review marker matching the contract hash. `/conduct` will refuse Phase 1 otherwise.
- [ ] **Sibling-slug pre-audit.** Run `ls docs/dev_plans/*.md` and confirm no real sibling shares ≥3 contiguous tokens with this plan's stripped slug `skill-improvements-from-usage-report` (after type-prefix `feature` is stripped). If a real match exists, record it in `## Findings` so the Phase 6 self-test invariant is updated to expect that `skipped:` line instead of the unconditional `audit: no sibling plans matched`.
- [ ] **Lock the Phase 6 `dev-plan create` baseline path** to one of: (a) stdout-only capture (no plan file written), or (b) throwaway branch checked out solely for the baseline and discarded after. Record the chosen path in `## Findings`. Do not leave the three-way fallback open.
- [ ] Add `docs/dev_plans/README.md` row for this plan as `Not Started` so reviewers can find it.
- [ ] **Do NOT run `just sync-skills`, `just check-sync`, or `just check-prompt-parity`** as drift checks at this point — pre-merge drift on the three target skills (and rubric byte-identity violations against `.codex/`) are expected. Drift detection is a Phase 6 concern post-promote.
- [ ] Commit: `docs: register skill-improvements plan in dev-plans index`.

### Phase 1: `deep-review` diff-scope + worktree-identity preflight
- [ ] Edit `.claude/skills/deep-review/SKILL.md`:
  - Resolve branch identity every run via `git rev-parse --show-toplevel` + `git branch --show-current`.
  - Banner: `Reviewing: <branch> @ <worktree-root> | <base>..<head> (<N> commits, <M> files)`.
  - In `--continue` resume mode, banner shows stored range with `(resume)` tag.
  - Concurrent-worktree informational line including the list of other worktrees: `Other worktrees present (informational): <count> (<root1>, ...); anchored to <root>`.
  - Trunk-vs-trunk halt with `git symbolic-ref refs/remotes/origin/HEAD` + main/master fallback. **Halt fires before review-state file write.**
  - `--continue` fallback banner extension.
  - "Confirm scope before dispatch" gate.
  - Cache-bypass posture documented (no-op contract if no harness cache exists).
- [ ] Edit `.claude/skills/deep-review/rubric.md`: append the verbatim criterion from Requirement 1; if the file's header self-declares byte-identical mirroring with `.codex/`, soften per the Review Focus self-claim rule.
- [ ] Phase 1 ships both files (`SKILL.md` + `rubric.md`) in one commit.
- [ ] Commit: `deep-review: print resolved diff range + worktree-identity preflight banner`.

### Phase 2: `dev-plan` Explore git-ref category
- [ ] Edit `.claude/skills/dev-plan/SKILL.md`: extend GENERIC EXPLORE PROMPT with `verified git refs` (verified + unverified subkeys); add a single canonical "Point-in-time facts" subsection in the Constraints block, referenced by the prompt body. Soften the GENERIC EXPLORE block self-claim header from "byte-identical mirror" to "intended to be mirrored byte-identically — see `CODEX_MIRROR_BACKLOG.md`".
- [ ] Edit `.claude/skills/dev-plan/rubric.md`: append the verbatim criterion from Requirement 2; soften the line-3 self-claim ("Mirrored byte-identically …") to "Intended to be mirrored byte-identically — see `CODEX_MIRROR_BACKLOG.md` for current drift."
- [ ] Phase 2 ships both files in one commit.
- [ ] Commit: `dev-plan: extend Explore to verify referenced git refs (point-in-time)`.

### Phase 3: `update-docs` sibling-slug audit extension
- [ ] Edit `.claude/skills/update-docs/SKILL.md`: extend the existing dev-plan audit pass with:
  - Audit scope explicitly limited to `docs/dev_plans/*.md`; `tests/fixtures/dev_plans/` excluded by default.
  - Slug match (≥3 contiguous hyphen-delimited tokens, no stop-word filter).
  - Component match (primary's `Files to Modify` paths → sibling body, case-insensitive substring).
  - Both fallbacks (filename convention, missing Files-to-Modify).
  - Sentinel string `audit: no sibling plans matched` for the no-match case.
  - Non-blocking surfacing + commit-preamble skip line.
  - Worked example.
- [ ] Commit: `update-docs: extend dev-plan audit with sibling-slug match and fixture-dir exclusion`.

### Phase 4: Pre-merge code review
- [ ] Run `/deep-review` against the feature branch using the **installed (pre-edit) `deep-review`**. The installed version still reviews the diff text (its job); the new banner won't print, but that's expected — banner verification is a Phase 6 concern post-`promote-skills`. The pre-merge value is the lens findings against the diff.
- [ ] **Pass criteria for Phase 4 review (explicit gate):**
  1. Zero Critical findings.
  2. Every Important finding has either a fix commit or a written defer-rationale in `## Findings`.
  3. Maximum **one** re-review iteration. Track manually: append `Re-review iteration: N/1` line to `## Findings` after each pass. If a second pass surfaces new Critical findings, halt and re-plan.
  4. Before any re-review, re-run `git diff $(git merge-base HEAD origin/main)..HEAD --stat` and confirm scope still matches the feature branch (per CLAUDE.md Review Workflow rule).
- [ ] Address findings via additional commits on the feature branch.

### Phase 5: Status flip + PR (terminal `/conduct` phase)
- [ ] Update `docs/dev_plans/README.md` to mark this plan **In Review** with the branch name.
- [ ] Commit: `docs: mark skill-improvements plan In Review`.
- [ ] Open PR; do not squash-merge (per global preference).
- [ ] **`/conduct` stops here.** The merge is an external async event (human reviewer + GitHub merge action). Phase 6 is a separate manual run after merge — `/conduct` does not advance past Phase 5 automatically.

### Phase 6: Post-merge — promotion, behavioral verification, badge flip
**Trigger: PR has been merged. Run manually.**

- [ ] Run `just promote-skills` to push `.claude/skills/` (now on main) → `~/.claude/skills/` global. This is when the new code becomes the installed code.
- [ ] Run `just check-sync` and confirm **no `drift:` lines for `deep-review`, `dev-plan`, or `update-docs` on the Claude side** (clean state is silent — `check-sync.sh` does not emit `ok:` lines). `skip:` lines on the Codex side are expected.
- [ ] **Behavioral fixture captures** (paste each transcript into this plan's `## Findings` as inline code blocks; no separate fixture files committed):
  - **`mode-full`** — `/deep-review` (no args) on a non-trunk feature branch (use any active feature branch). Capture banner output.
  - **`mode-pr`** — `/deep-review --pr <N>` where `<N>` is this PR's merged number (recorded in `## Findings` at PR open). PR #15 in the original draft is now merged and not reusable. Banner invariant: matches the literal regex `Reviewing: .* @ .* \| origin/[^.]+\.\.[0-9a-f]+ \(\d+ commits, \d+ files\)`.
  - **`mode-continue-schema-mismatch`** — corrupt `.deep-review/latest-claude.json` (e.g. `echo '{}' > .deep-review/latest-claude.json`), run `--continue`. AC: schema-mismatch warning prints first; banner shows fresh-resolved range with no `(resume)` tag.
  - **`mode-worktree-identity-cross-branch`** — invoke `/deep-review` on branch A, `git checkout` branch B in the same worktree, invoke again. AC: second banner shows branch B's identity, not A's. Demonstrates per-invocation resolution independent of any harness cache.
  - **`mode-continue-resume`** — `--continue` immediately after a prior `/deep-review` run on the same HEAD. AC: banner shows stored range with `(resume)` tag; grep stored `head_commit` from `.deep-review/latest-claude.json` and assert it appears in transcript.
  - **`mode-continue-fallback`** — synthesise fallback via `git checkout --detach` + back, run `--continue`. Verify banner is appended to the existing fallback warning.
  - **`halt-trunk`** — `rm -f .deep-review/latest-claude.json` first; checkout main; run `/deep-review`; verify halt message and that `.deep-review/latest-claude.json` does NOT exist after (assert via `! -f .deep-review/latest-claude.json`).
  - **`worktree-banner`** — `git worktree add ../skills.md-sibling`; from the original worktree run `/deep-review` and capture the informational line listing the sibling. **Cleanup**: `git worktree remove ../skills.md-sibling && git worktree prune`; AC: `git worktree list | wc -l == 1` after cleanup.
- [ ] **Backward-compat baselines** (paste each into `## Findings`; specify invariants per fixture):
  - `/deep-review` (no args) on a feature branch — invariant: contains `Reviewing: <branch> @`, exit code 0, no `Refusing to review` substring.
  - `/deep-review --pr <N>` (the merged PR number for this plan, locked in Phase 5) — invariant: matches `Reviewing: .* @ .* \| origin/[^.]+\.\.[0-9a-f]+ \(\d+ commits, \d+ files\)`.
  - `/deep-review --continue` after a prior run — invariant: contains `(resume)` tag.
  - `/dev-plan create` — uses the path locked in Phase 0 (stdout-only OR throwaway branch). Invariant: Explore output includes `### Verified git refs` header **and** demonstrates all three ref-pattern forms. Construct the request to mention: a real branch (`feature/skill-improvements-from-usage-report`), a bogus tag (`v999.999.999`), and a `<name>@<sha>` form (`HEAD@deadbeefdeadbeefdeadbeefdeadbeefdeadbeef`). AC: at least one entry per pattern; unverified entries cite at least one of the three reason strings (`tag not found`, `branch tracks gone-remote`, `sha unknown`).
  - `/update-docs` against a fixture README at `tests/fixtures/scratch-readme.md` (create the fixture file specifically for this baseline; commit it under `tests/fixtures/` if persistent verification is desired, otherwise revert post-capture). **Do not invoke against the repo root README.** Invariant: no `audit:` line in transcript (since target is not a dev plan).
  - **Slug-match positive baseline** — invoke `/update-docs` against this plan as primary with at least one synthetic sibling under `docs/dev_plans/` whose stripped slug shares ≥3 contiguous tokens (create the synthetic sibling for the baseline only, capture transcript, then revert). AC: transcript contains a `skipped: <slug> (<reason>)` line for the synthetic sibling, demonstrating the positive path.
  - **Filename-convention fallback** — invoke `/update-docs` against a hand-named plan (no `YYYYMMDD-` prefix; create solely for this baseline). AC: transcript contains the documented one-line fallback note.
- [ ] **`update-docs` sibling-audit self-test** (run BEFORE flipping plan status to Complete). Invoke `update-docs` against this plan as primary. Expected output: `audit: no sibling plans matched` (since the only fixture-style siblings are excluded by the new audit-scope rule). Capture both the audit output and the resulting commit-message preamble (which should contain no `skipped:` lines) into `## Findings`. This verifies the commit-preamble AC.
- [ ] **Cache-bypass verification** (only if a harness cache surface exists): inject a stale cached branch value, invoke `/deep-review`, assert the banner shows live `git branch --show-current` not the stale value. If no cache surface exists in this Claude harness, document explicitly in `## Findings`: "No harness cache surface; per-invocation resolution is the only path; cache-bypass is a no-op contract."
- [ ] **Badge flips** in `~/.claude/usage-data/report.html`:
  - **`expected_delta_NOT_FIXED = 3`** (locked). Flip the three badges for **deep-review** (scope/reconciliation), **dev-plan** (freshness), and **update-docs** (sibling auto-detection). The **conduct** marker-hash row stays NOT FIXED — its status-note is updated to cite commit `59daefc` as a partial fix (workspace-split addresses Progress/Findings appends but not above-marker writes) and to flag a follow-up plan for true marker auto-refresh on phase content writes.
  - Capture pre-flip count: `grep -c 'NOT FIXED' ~/.claude/usage-data/report.html`. Record in `## Findings`.
  - Flip the three badges; each FIXED badge cites this PR's merged commit hash and the **actual merge date** (e.g., `2026-05-DD`, the unique date string, not just `2026-05`).
  - Update the conduct-row status-note inline with the partial-fix wording above (do not flip its badge).
  - Capture post-flip count; assert `pre - post == 3`.
  - `grep -c 'FIXED.*<merge-date>'` should increase by `3`. Record both counts.
- [ ] **Codex backlog artifact.** Append a tracked entry to `docs/dev_plans/CODEX_MIRROR_BACKLOG.md` (create the file if absent) listing: this PR's commit hashes; the **five** `.codex/` files needing mirroring (`.codex/skills/deep-review/SKILL.md`, `.codex/skills/deep-review/rubric.md`, `.codex/skills/dev-plan/SKILL.md`, `.codex/skills/dev-plan/rubric.md`, `.codex/skills/update-docs/SKILL.md`); and `just check-prompt-parity` as the gating check the Codex maintainer must clear (currently expected to exit 1 against `deep-review` and `dev-plan` rubrics until mirroring lands). This makes the deferred-parity debt visible beyond a one-off message.
- [ ] After all verifications pass and `## Findings` is populated, mark plan status Complete via `/dev-plan complete`.

## Constraints

- **Skills mirror policy.** Edit `.claude/skills/<skill>/SKILL.md` only. Never touch `.codex/skills/` directly.
- **No new infrastructure.** Text edits to existing SKILL.md / rubric.md files only. No new tools, no new helper scripts.
- **Backward-compatible (refined).** Every skill remains invocable with existing flags, except where new halts intentionally trigger on previously-silent-wrong-output cases.
- **One commit per skill.** Phases 1, 2, 3 each ship one focused commit (Phases 1 and 2 each include their rubric edit in the same commit). Phase 0, Phase 5 status flip are separate single-purpose commits.
- **Workflow direction is repo → global, post-merge.** `just sync-skills` (global → repo) is NOT used. `just promote-skills` (repo → global) runs only at Phase 6.
- **No pre-merge writes to `~/.claude/skills/`.** No scratch promotions, no global mutations between Phase 0 and Phase 6.
- **Halt before write.** `deep-review`'s SKILL.md prompt instructs the model to halt before `.deep-review/latest-claude.json` is written. Enforcement is prompt-driven (no executable guard); the Phase 6 `halt-trunk` fixture's post-condition (`! -f .deep-review/latest-claude.json`) is the verification.
- **Worktree-identity is per-invocation.** `deep-review` resolves identity every run; never relies on cached values.
- **`/conduct` stops at Phase 5.** Phase 6 is a separate manual run after PR merge.
- **Behavioral verification is post-merge only.** Pre-merge Phase 4 is code-level review against the diff using the installed (pre-edit) skills. New behaviors are verified at Phase 6 after `promote-skills`.
- **Phase 6 self-test runs BEFORE Complete status flip.** `update-docs` audit behavior on a Complete plan is not verified by this plan; running the self-test pre-Complete avoids that ambiguity.
- **Phase 6 fixtures embed in `## Findings`, not in `tests/fixtures/`.** Avoids a separate post-merge fixture-commit PR. The exception is `tests/fixtures/scratch-readme.md` if needed for the `/update-docs` baseline; that is a single optional file.

## Acceptance Criteria

- [ ] `deep-review` prints `Reviewing: <branch> @ <worktree-root> | <base>..<head> (<N> commits, <M> files)` before any lens spawns. Verified by `mode-full` / `mode-pr` / `mode-continue-resume` / `mode-continue-fallback` transcripts in `## Findings`.
- [ ] `--continue` resume-mode banner shows stored range with `(resume)` tag and the stored `head_commit` SHA appears in the transcript. Verified by `mode-continue-resume` fixture.
- [ ] `--continue` fallback warning has the resolved-range banner appended. Verified by `mode-continue-fallback` fixture.
- [ ] `deep-review` from a worktree when a sibling worktree exists prints the `Other worktrees present (informational):` line including the list of siblings. Worktree fixture cleaned up afterward (`git worktree list | wc -l == 1`). Verified by `worktree-banner` fixture.
- [ ] `deep-review` on the configured trunk without `--pr`/`--continue` halts with the documented message and `.deep-review/latest-claude.json` does not exist after the halt (pre-state pinned via `rm -f`). Verified by `halt-trunk` fixture.
- [ ] Cache-bypass behavior: either a positive fixture demonstrating bypass, or an explicit `## Findings` note that no harness cache surface exists.
- [ ] `dev-plan` Explore output for a request mentioning a real branch (`feature/skill-improvements-from-usage-report`), a bogus tag (`v999.999.999`), and a `<name>@<sha>` form (`HEAD@deadbeef…`) includes one entry per pattern under `verified git refs` with the asymmetric subkeys; unverified entries cite at least one of the three documented reason strings (`tag not found`, `branch tracks gone-remote`, `sha unknown`).
- [ ] `deep-review` per-invocation worktree-identity is verified by either (a) the `mode-worktree-identity-cross-branch` fixture (positive: branch-A then branch-B invocation banners differ), or (b) an explicit `## Findings` note that no harness cache surface exists AND the cross-branch fixture nonetheless demonstrates fresh resolution.
- [ ] `dev-plan/rubric.md` includes the verbatim criterion: `grep -F 'point-in-time disclaimer; ref drift after create' .claude/skills/dev-plan/rubric.md` returns ≥1.
- [ ] `deep-review/rubric.md` includes the verbatim criterion: `grep -F 'trunk-vs-trunk halt fires before any state-file write' .claude/skills/deep-review/rubric.md` returns ≥1.
- [ ] `update-docs` invoked with this plan as primary post-merge prints `audit: no sibling plans matched`; commit-message preamble has no `skipped:` lines. Verified by Phase 6 self-test capture.
- [ ] `update-docs` audit excludes `tests/fixtures/dev_plans/` from slug-match scope. Verified by inspecting the SKILL.md edit AND by the self-test outcome (which depends on the exclusion).
- [ ] Each skill remains invocable with its pre-change argument forms enumerated in Phase 6 backward-compat baselines, with the per-fixture invariants holding (grep assertions). Trunk-vs-trunk halt is an intentional new behavior, not a regression.
- [ ] Phase 6 `just check-sync` emits **no `drift:` lines** for the three target skills on the Claude side (clean state is silent — the script does not print `ok:`); Codex `skip:` lines are expected.
- [ ] Re-review iteration count: `grep 'Re-review iteration' <plan-file>` (within the `## Findings` section) shows `N/1` with N ≤ 1.
- [ ] `~/.claude/usage-data/report.html` deltas: `pre_NOT_FIXED - post_NOT_FIXED == 3` (locked: deep-review, dev-plan, update-docs flipped; conduct row stays NOT FIXED with updated status-note citing `59daefc` as partial fix); `grep -c 'FIXED.*<merge-date>'` increases by 3. Both pre/post counts recorded in `## Findings`.
- [ ] `docs/dev_plans/CODEX_MIRROR_BACKLOG.md` has a new entry with this PR's commit hashes, the **five** `.codex/` files needing mirror, and `just check-prompt-parity` listed as the gating check.
- [ ] `mode-pr` banner matches the literal regex `Reviewing: .* @ .* \| origin/[^.]+\.\.[0-9a-f]+ \(\d+ commits, \d+ files\)`.
- [ ] `mode-continue-schema-mismatch` fixture: schema-mismatch warning prints first; banner shows fresh-resolved range with no `(resume)` tag.
- [ ] Slug-match positive baseline: transcript contains a `skipped: <slug> (<reason>)` line for the synthetic sibling.
- [ ] Filename-convention fallback baseline: transcript contains the documented one-line fallback note.

<!-- reviewed: 2026-05-04 @ 9fd33a052eff28f8d755f6d0acb4531f0a93f50b -->

## Progress

- [x] Phase 0: Pre-flight (commit `93d5e66`)
- [x] Phase 1: `deep-review` diff-scope + worktree-identity preflight (commit `c318c2f`)
- [x] Phase 2: `dev-plan` Explore git-ref category (commit `5e8f6ac`)
- [x] Phase 3: `update-docs` sibling-slug audit extension (commit `4131fd9`)
- [x] Phase 4: Pre-merge code review (fix-up commit `bbf3c1a`; review iteration 1/1)
- [x] Phase 5: Status flip + PR (commits `1536ec8`, `61dc2cd`; PR #16)
- [ ] Phase 6: Post-merge — promotion, behavioral verification, badge flip *(manual, post-merge; Codex mirror parity completed 2026-05-06, Claude runtime fixtures/badge flip not re-run by Codex)*

## Findings

### Phase 4 — pre-merge code review (2026-05-04)

Re-review iteration: 1/1.

**Critical**: 0
**Important**: 4 (3 fixed in commit at end of Phase 4; 1 deferred with rationale)
**Minor**: 2 (deferred)

**Fixed**:
- `dev-plan/rubric.md` lines 8 + 40 said "three fact categories"; updated to "four" to match the new `verified git refs` category.
- `deep-review/SKILL.md` §0 step 3 risked double-printing the concurrent-worktree informational line; rewritten to "detect here, print in §1a".
- `deep-review/SKILL.md` §0 step 2 trunk-fallback used `git for-each-ref … | head -n 1` as last-resort, which would spuriously halt single-branch repos. Removed the fallback; if neither `origin/HEAD` nor local `main`/`master` exists, halt is skipped (no configured trunk).

**Deferred (with rationale)**:
- *Schema-mismatch + missing-state-file merged in §1a row 2.* The reviewer flagged that the plan distinguishes the two cases. **Rationale**: the existing `Review State` section (line 33) already treats them identically ("If the state file is missing, or `schema_version` is absent / does not match the current expected version (1), treat `--continue` as `--full` with a warning"). Merging them in the new banner row preserves consistency with the pre-existing contract. Splitting would require a corresponding split in `Review State`, which expands scope.
- *update-docs worked-example intermediate reasoning is muddled.* Conclusion is correct (no slug match), only the explanatory sentence is loose. Cosmetic; deferred to a future docs polish pass.
- *README row shows "Not Started" while Phases 1–3 are implemented.* Expected per the plan — Phase 5 flips status to "In Review" once the PR is opened.

### Codex mirror work deferred (2026-05-04)

User credits exhausted for this week — Codex mirror work resumes **after 2026-05-06**. This is already the structural plan (`.codex/` edits are `[CODEX-DEFERRED]` throughout, tracked in `CODEX_MIRROR_BACKLOG.md` to be created in Phase 6). The deferral is on the maintainer's calendar, not the plan: no scope change.

**Pick-up checklist for the next session:**
- Mirror the five `.codex/` files: `.codex/skills/{deep-review,dev-plan,update-docs}/SKILL.md` and `.codex/skills/{deep-review,dev-plan}/rubric.md`.
- Re-run `just check-prompt-parity` until clean for `deep-review` and `dev-plan`.
- Re-run `just check-trunk-snippet-parity` if the Codex mirrors of `deep-review`/`update-docs` carry the same snippet — extend `TARGETS` in the script if so.
- Then proceed with Phase 6 (post-merge promotion + behavioural verification + badge flips).

### Codex mirror parity completed (2026-05-06)

Codex adapted the PR #16 Claude-side changes into the Codex skill mirrors, preserving byte-identical rubric parity and shared generic prompt blocks while keeping Codex-native `spawn_agent`, model-tier, and `.deep-review/latest-codex.json` wording where the harnesses legitimately diverge.

**Files mirrored/adapted:**
- `.codex/skills/deep-review/SKILL.md`
- `.codex/skills/deep-review/rubric.md`
- `.codex/skills/dev-plan/SKILL.md`
- `.codex/skills/dev-plan/rubric.md`
- `.codex/skills/update-docs/SKILL.md`
- `scripts/check-trunk-snippet-parity.sh` now includes the Codex deep-review and update-docs copies in `TARGETS`.

**Validation:**
```text
just promote-skills
just check-sync
just check-prompt-parity
just check-trunk-snippet-parity
just lint-scripts
```

All five commands passed on 2026-05-06 after the Codex mirror adaptation.

**Phase 6 boundary note:** Codex did not re-run Claude interactive slash-command behavioural fixtures (`mode-full`, `mode-pr`, continuation modes, worktree banner, or badge-flip transcripts). The live `~/.claude/usage-data/report.html` already reports PR #16 as shipped/promoted and currently has `grep -c 'NOT FIXED' == 3`; the remaining NOT FIXED badges/notes are conduct marker-hash related, so Codex did not flip them. `docs/dev_plans/CODEX_MIRROR_BACKLOG.md` now records that the PR #16 Codex mirror is parity-clean as of 2026-05-06.

### Post-Phase-5 deep-review pass (2026-05-04)

Run on the full PR diff after Phase 5. **Critical: 0; Important: 3; Minor: 2.** All five fixed in one fix-up commit on the PR.

**Fixed**:
- *deep-review §0/§1a — detached HEAD case.* `BRANCH=""` would print a banner with an empty branch field. Fix: §0 step 1 now states "if `$BRANCH` is empty, use `(detached HEAD @ <short-sha>)` in the banner and skip the trunk-vs-trunk halt"; §0 step 2 gates on `$BRANCH` non-empty.
- *update-docs slug-match — type-prefix double-strip.* `20260504-feature-feature.md` would lose a genuine `feature` token. Fix: only strip the leading type token when the remainder still has ≥2 tokens.
- *update-docs slug-match — recall trade-off undocumented.* The ≥3-token rule is deliberate (high-precision signal; component match is the recall safety net) but wasn't stated. Fix: explicit "Recall trade-off (deliberate)" paragraph added.
- *deep-review §0/§1a — implicit cross-section state.* §0 step 3 said "remember for §1a" with risk of silent drop on reordering. Fix: §0 step 3 deleted; `git worktree list` is now called once inline in §1a.
- *Trunk-resolution snippet duplication — no parity gate.* Fix: added `scripts/check-trunk-snippet-parity.sh` + `just check-trunk-snippet-parity` recipe. The check immediately surfaced real drift (update-docs still had the buggy `for-each-ref | head -n 1` fallback that Phase 4 fixed in deep-review). Aligned update-docs to the safer `BASE=""` behaviour.

## Issues & Solutions

(populated by `/conduct`)

## Final Results

(populated by `/conduct`)
