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

## Usage

Copy the relevant skills directory into your project or symlink it.
