#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
	# shellcheck disable=SC1091
	source "$ROOT_DIR/.env"
fi

GLOBAL_CODEX_SKILLS_DIR="${GLOBAL_CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
GLOBAL_CLAUDE_SKILLS_DIR="${GLOBAL_CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MANAGED_SKILLS="${MANAGED_SKILLS:-content-draft content-review dev-plan fan-out update-docs}"
GLOBAL_CODEX_AGENTS="${GLOBAL_CODEX_AGENTS:-$HOME/.codex/AGENTS.md}"
GLOBAL_CLAUDE_MD="${GLOBAL_CLAUDE_MD:-$HOME/.claude/CLAUDE.md}"

if [[ "${1:-}" != "--yes" ]]; then
	echo "error: promotion is destructive; rerun with --yes" >&2
	exit 1
fi

read -r -a managed_skills <<<"$MANAGED_SKILLS"

copy_guidelines_to_global() {
	local repo_guidelines_code="$ROOT_DIR/.codex/skills/content-review/references/content-guidelines.md"
	local repo_guidelines_claude="$ROOT_DIR/.claude/skills/content-review/references/content-guidelines.md"
	local global_guidelines_code="$GLOBAL_CODEX_SKILLS_DIR/content-review/references/content-guidelines.md"
	local global_guidelines_claude="$GLOBAL_CLAUDE_SKILLS_DIR/content-review/references/content-guidelines.md"

	mkdir -p "$(dirname "$global_guidelines_code")" "$(dirname "$global_guidelines_claude")"
	cp "$repo_guidelines_code" "$global_guidelines_code"
	cp "$repo_guidelines_claude" "$global_guidelines_claude"
	echo "Copied canonical repo content-guidelines.md to global skill directories"
}

for skill in "${managed_skills[@]}"; do
	mkdir -p "$GLOBAL_CODEX_SKILLS_DIR/$skill" "$GLOBAL_CLAUDE_SKILLS_DIR/$skill"
	rsync -a --delete "$ROOT_DIR/.codex/skills/$skill/" "$GLOBAL_CODEX_SKILLS_DIR/$skill/"
	rsync -a --delete "$ROOT_DIR/.claude/skills/$skill/" "$GLOBAL_CLAUDE_SKILLS_DIR/$skill/"
done

if [[ " $MANAGED_SKILLS " == *" content-review "* ]]; then
	copy_guidelines_to_global
fi

REPO_CLAUDE_MD="$ROOT_DIR/.claude/CLAUDE.md"
if [[ -f "$REPO_CLAUDE_MD" ]]; then
	mkdir -p "$(dirname "$GLOBAL_CLAUDE_MD")"
	cp "$REPO_CLAUDE_MD" "$GLOBAL_CLAUDE_MD"
	echo "Promoted CLAUDE.md: $REPO_CLAUDE_MD -> $GLOBAL_CLAUDE_MD"
else
	echo "warn: repo CLAUDE.md not found at $REPO_CLAUDE_MD, skipping" >&2
fi

REPO_CODEX_AGENTS="$ROOT_DIR/.codex/AGENTS.md"
if [[ -f "$REPO_CODEX_AGENTS" ]]; then
	mkdir -p "$(dirname "$GLOBAL_CODEX_AGENTS")"
	cp "$REPO_CODEX_AGENTS" "$GLOBAL_CODEX_AGENTS"
	echo "Promoted AGENTS.md: $REPO_CODEX_AGENTS -> $GLOBAL_CODEX_AGENTS"
else
	echo "warn: repo AGENTS.md not found at $REPO_CODEX_AGENTS, skipping" >&2
fi

echo "Promotion complete: repo -> global"
