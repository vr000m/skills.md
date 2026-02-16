# skills.md

Reusable skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [OpenAI Codex CLI](https://github.com/openai/codex) agents.

## Structure

- `.claude/skills/` -- Skills for Claude Code (`/slash-command` style)
- `.codex/skills/` -- Skills for OpenAI Codex CLI

## Skills

| Skill | Claude | Codex | Description |
|-------|--------|-------|-------------|
| dev-plan | Yes | Yes | Generate and manage development plans |
| fan-out | Yes | Yes | Parallel agent orchestration via worktrees |
| content-draft | Yes | Yes | Draft content following style guidelines |
| content-review | Yes | Yes | Review content against style guidelines |

## Authority Model

Default authority is global skills, not this repo.

- Global Codex authority: `~/.codex/skills`
- Global Claude authority: `~/.claude/skills`
- Managed scope: only skills in `MANAGED_SKILLS` are synced/checked/promoted/bootstrapped
- Content guidelines authority (in priority order):
  1. `CONTENT_GUIDELINES_LOCAL` from `.env` (if file exists)
  2. `CONTENT_GUIDELINES_URL` (raw GitHub URL)
  3. repo copy only as fallback while bootstrapping

## Workflow

- Day-to-day: run `just sync-skills` to mirror `global -> repo`
- Intentional overwrite: run `just promote-skills` to set `repo -> global`
- New machine setup: run `just bootstrap-skills` (initialises missing managed skills only)
- Force bootstrap overwrite when needed: run `just bootstrap-skills-force`
- Validation: run `just check-sync`

Notes:
- `promote-skills` and `bootstrap-skills` refresh global `content-guidelines.md` when `content-review` is in `MANAGED_SKILLS`.
- `bootstrap-skills` is non-destructive unless `--force` is provided.
- If local/remote authoritative guidelines are unavailable, scripts fall back to the repo `content-guidelines.md` copy and print a warning.

## Conflict Policy

Treat conflicts as policy decisions, not merge-resolution tasks.

- Repo-only drift: run `just sync-skills` (discard) or `just promote-skills` (adopt)
- Global-only drift: run `just sync-skills`
- Both changed: decide authority explicitly, then sync again

## Setup

1. Install tools:

```bash
brew install just shellcheck shfmt
```

2. Create local env file:

```bash
cp .env.example .env
```

3. Set your local content-guidelines path in `.env`:

```bash
CONTENT_GUIDELINES_LOCAL="/Users/vr000m/Code/vr000m/varunsingh.net/.claude/content-guidelines.md"
```

4. (Optional) restrict managed skills:

```bash
MANAGED_SKILLS="content-draft content-review dev-plan fan-out"
```

## Commands

- `just sync-skills`
- `just promote-skills`
- `just bootstrap-skills`
- `just bootstrap-skills-force`
- `just check-sync`
- `just lint-scripts`
