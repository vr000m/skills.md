# skills.md

Reusable skills repo for Claude Code and OpenAI Codex CLI agents.

## Commands

```bash
just sync-skills        # Mirror global -> repo (day-to-day)
just promote-skills     # Set repo -> global (intentional overwrite)
just bootstrap-skills   # Init missing managed skills on new machine
just bootstrap-skills-force  # Force overwrite bootstrap
just check-sync         # Validate sync state
just lint-scripts       # shellcheck + shfmt on scripts/
```

Requires: `brew install just shellcheck shfmt`

## Architecture

```
.claude/skills/     Claude Code skills (SKILL.md per skill)
.codex/skills/      Codex CLI skills (mirrored structure)
scripts/            Shell scripts for sync/promote/bootstrap/check
docs/dev_plans/     Development plans
justfile            Task runner config
.env.example        Template for local env overrides
```

## Authority Model

Global is authoritative, repo is a mirror:
- Global skills: `~/.claude/skills/` and `~/.codex/skills/`
- `sync-skills` copies global -> repo; `promote-skills` copies repo -> global
- `~/.claude/CLAUDE.md` syncs bidirectionally with `.claude/CLAUDE.md`
- `~/.codex/AGENTS.md` syncs bidirectionally with `.codex/AGENTS.md`
- Only skills listed in `MANAGED_SKILLS` (from `.env` or a per-command env override) are synced
- Content guidelines authority: repo-canonical file at `.codex/skills/content-review/references/content-guidelines.md`
- Repo Claude mirror: `.claude/skills/content-review/references/content-guidelines.md`
- Global mirrors: `~/.codex/skills/content-review/references/content-guidelines.md` and `~/.claude/skills/content-review/references/content-guidelines.md`

## Skill Workflow

Recommended development workflow using skills:

1. `/dev-plan create feature xyz` — Create the plan
2. `/review-plan` — Audit plan for gaps and undocumented assumptions (blocks until complete)
3. Address review findings, update plan as needed
4. `/fan-out` — Fan out independent tasks to parallel agents (or implement manually)

## Sync Workflow

- Day-to-day: run `just sync-skills` to mirror `global -> repo`
- Intentional overwrite: run `just promote-skills` to set `repo -> global`
- New machine setup: run `just bootstrap-skills` (initialises missing managed skills only)
- Force bootstrap overwrite when needed: run `just bootstrap-skills-force`
- Seed or promote only a subset for one run: prefix the command with `MANAGED_SKILLS="skill-a skill-b"`
- Validation: run `just check-sync`

Notes:
- All commands sync `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` alongside managed skills.
- `promote-skills` and `bootstrap-skills` copy the repo-canonical `content-review/references/` directory into global skill directories when `content-review` is in `MANAGED_SKILLS`.
- `bootstrap-skills` is non-destructive unless `--force` is provided (applies to skills, reference files, CLAUDE.md, and AGENTS.md).
- `promote-skills` is destructive for the selected managed skills (`rsync --delete`) and always overwrites global `CLAUDE.md` and `AGENTS.md`.
- `sync-skills` and `check-sync` skip managed skills that do not exist yet in the global authorities and tell you to seed them with `bootstrap-skills` or `promote-skills`.
- `sync-skills` preserves the entire repo-canonical `references/` directory for content-review (does not overwrite from global) and refreshes the repo Claude copy from the canonical codex source.
- `check-sync` requires both `content-guidelines.md` and `writing-style-rules.md` in the canonical references directory.
- `sync-skills` warns for missing global `AGENTS.md` only when repo `.codex/AGENTS.md` exists.

## Conflict Policy

Treat conflicts as policy decisions, not merge-resolution tasks.

- Repo-only drift: run `just sync-skills` (discard) or `just promote-skills` (adopt)
- Global-only drift: run `just sync-skills`
- Both changed: decide authority explicitly, then sync again

## Gotchas

- **Don't edit `.claude/CLAUDE.md` or `.codex/AGENTS.md` directly** -- they get overwritten by `sync-skills`. Edit the global files instead, then sync.
- Content guidelines are repo-canonical at `.codex/skills/content-review/references/content-guidelines.md`, mirrored to `.claude/skills/content-review/references/content-guidelines.md` and the global skill folders
- `bootstrap-skills` is non-destructive by default; use `--force` to overwrite
- Scope one command without changing `.env`: `MANAGED_SKILLS="rfc-finder" just bootstrap-skills` or `MANAGED_SKILLS="rfc-finder" just promote-skills`
- Even when you scope `MANAGED_SKILLS`, `promote-skills` still copies repo `.claude/CLAUDE.md` and `.codex/AGENTS.md` to the global paths
- `.env` is optional; copy from `.env.example` only if you want local overrides such as `MANAGED_SKILLS`
