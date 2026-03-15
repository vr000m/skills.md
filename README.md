# skills.md

Reusable skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [OpenAI Codex CLI](https://github.com/openai/codex) agents.

## Skills

| Skill | Claude | Codex | Description |
|-------|--------|-------|-------------|
| dev-plan | Yes | Yes | Generate and manage development plans |
| fan-out | Yes | Yes | Parallel agent orchestration via worktrees |
| content-draft | Yes | Yes | Draft content following style guidelines |
| content-review | Yes | Yes | Review content against style guidelines |
| rfc-finder | Yes | Yes | Find and link to IETF RFCs and related drafts |
| spec-compliance | Yes | Yes | Check code against RFC/W3C/WHATWG requirements |
| update-docs | Yes | Yes | Audit and update stale docs against branch diffs |

## Setup

1. Install tools:

```bash
brew install just shellcheck shfmt
```

2. Create local env file:

```bash
cp .env.example .env
```

3. (Optional) restrict managed skills in `.env`:

```bash
MANAGED_SKILLS="content-draft content-review dev-plan fan-out review-plan rfc-finder spec-compliance update-docs"
```

For one-off runs, prefer a command-scoped override instead of editing `.env`:

```bash
MANAGED_SKILLS="rfc-finder" just bootstrap-skills
MANAGED_SKILLS="rfc-finder" just promote-skills
```

`bootstrap-skills` seeds missing global skill dirs without overwriting existing content unless `--force` is used. `promote-skills` intentionally overwrites the selected managed skills and also copies repo `.claude/CLAUDE.md` and `.codex/AGENTS.md` to the global paths.

See [AGENTS.md](AGENTS.md) for commands, architecture, authority model, and workflow details.
