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
- Only skills listed in `MANAGED_SKILLS` (from `.env`) are synced
- Content guidelines authority: repo-canonical file at `.codex/skills/content-review/references/content-guidelines.md`
- Repo Claude mirror: `.claude/skills/content-review/references/content-guidelines.md`
- Global mirrors: `~/.codex/skills/content-review/references/content-guidelines.md` and `~/.claude/skills/content-review/references/content-guidelines.md`

## Workflow

- Day-to-day: run `just sync-skills` to mirror `global -> repo`
- Intentional overwrite: run `just promote-skills` to set `repo -> global`
- New machine setup: run `just bootstrap-skills` (initialises missing managed skills only)
- Force bootstrap overwrite when needed: run `just bootstrap-skills-force`
- Validation: run `just check-sync`

Notes:
- All commands sync `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` alongside managed skills.
- `promote-skills` and `bootstrap-skills` copy the repo-canonical `content-guidelines.md` into global skill directories when `content-review` is in `MANAGED_SKILLS`.
- `bootstrap-skills` is non-destructive unless `--force` is provided (applies to skills, CLAUDE.md, and AGENTS.md).
- `sync-skills` preserves repo-canonical `content-guidelines.md` (does not overwrite it from global) and refreshes the repo Claude copy from the canonical file.
- `sync-skills` warns for missing global `AGENTS.md` only when repo `.codex/AGENTS.md` exists.

## Conflict Policy

Treat conflicts as policy decisions, not merge-resolution tasks.

- Repo-only drift: run `just sync-skills` (discard) or `just promote-skills` (adopt)
- Global-only drift: run `just sync-skills`
- Both changed: decide authority explicitly, then sync again

## Gotchas

- **Don't edit `.claude/CLAUDE.md` or `.codex/AGENTS.md` directly** -- they get overwritten by `sync-skills`. Edit the global files instead, then sync.
- Content guidelines priority: `.env` local path > remote URL > repo fallback
- `bootstrap-skills` is non-destructive by default; use `--force` to overwrite
- Scripts expect `.env` to exist (copy from `.env.example`)
