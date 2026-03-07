# skills.md

Reusable skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [OpenAI Codex CLI](https://github.com/openai/codex) agents.

## Skills

| Skill | Claude | Codex | Description |
|-------|--------|-------|-------------|
| dev-plan | Yes | Yes | Generate and manage development plans |
| fan-out | Yes | Yes | Parallel agent orchestration via worktrees |
| content-draft | Yes | Yes | Draft content following style guidelines |
| content-review | Yes | Yes | Review content against style guidelines |
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
MANAGED_SKILLS="content-draft content-review dev-plan fan-out update-docs"
```

See [AGENTS.md](AGENTS.md) for commands, architecture, authority model, and workflow details.
