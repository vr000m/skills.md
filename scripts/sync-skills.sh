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

REPO_CODEX_DIR="$ROOT_DIR/.codex/skills"
REPO_CLAUDE_DIR="$ROOT_DIR/.claude/skills"
REPO_CLAUDE_MD="$ROOT_DIR/.claude/CLAUDE.md"
REPO_CODEX_AGENTS="$ROOT_DIR/.codex/AGENTS.md"

require_dir() {
	local path="$1"
	local name="$2"
	if [[ ! -d "$path" ]]; then
		echo "error: missing $name at $path" >&2
		exit 1
	fi
}

sync_repo_guidelines_copies() {
	local repo_guidelines_code="$REPO_CODEX_DIR/content-review/references/content-guidelines.md"
	local repo_guidelines_claude="$REPO_CLAUDE_DIR/content-review/references/content-guidelines.md"

	if [[ ! -f "$repo_guidelines_code" ]]; then
		echo "error: missing canonical content-guidelines.md at $repo_guidelines_code" >&2
		exit 1
	fi

	cp "$repo_guidelines_code" "$repo_guidelines_claude"
	echo "Restored repo content-guidelines.md copies from canonical source"
}

sync_skill() {
	local source_root="$1"
	local target_root="$2"
	local skill="$3"
	local source_dir="$source_root/$skill"
	local target_dir="$target_root/$skill"

	require_dir "$source_dir" "managed skill '$skill' in $source_root"
	mkdir -p "$target_dir"
	if [[ "$skill" == "content-review" ]]; then
		rsync -a --delete --exclude='references/content-guidelines.md' "$source_dir/" "$target_dir/"
	else
		rsync -a --delete "$source_dir/" "$target_dir/"
	fi
}

require_dir "$GLOBAL_CODEX_SKILLS_DIR" "GLOBAL_CODEX_SKILLS_DIR"
require_dir "$GLOBAL_CLAUDE_SKILLS_DIR" "GLOBAL_CLAUDE_SKILLS_DIR"
require_dir "$REPO_CODEX_DIR" "repo codex skills dir"
require_dir "$REPO_CLAUDE_DIR" "repo claude skills dir"

read -r -a managed_skills <<<"$MANAGED_SKILLS"
for skill in "${managed_skills[@]}"; do
	sync_skill "$GLOBAL_CODEX_SKILLS_DIR" "$REPO_CODEX_DIR" "$skill"
	sync_skill "$GLOBAL_CLAUDE_SKILLS_DIR" "$REPO_CLAUDE_DIR" "$skill"
done

if [[ " $MANAGED_SKILLS " == *" content-review "* ]]; then
	sync_repo_guidelines_copies
fi

if [[ -f "$GLOBAL_CLAUDE_MD" ]]; then
	cp "$GLOBAL_CLAUDE_MD" "$REPO_CLAUDE_MD"
	echo "Synced CLAUDE.md: $GLOBAL_CLAUDE_MD -> $REPO_CLAUDE_MD"
else
	echo "warn: global CLAUDE.md not found at $GLOBAL_CLAUDE_MD, skipping" >&2
fi

if [[ -f "$GLOBAL_CODEX_AGENTS" ]]; then
	cp "$GLOBAL_CODEX_AGENTS" "$REPO_CODEX_AGENTS"
	echo "Synced AGENTS.md: $GLOBAL_CODEX_AGENTS -> $REPO_CODEX_AGENTS"
else
	if [[ -f "$REPO_CODEX_AGENTS" ]]; then
		echo "warn: global AGENTS.md not found at $GLOBAL_CODEX_AGENTS, skipping" >&2
	fi
fi

echo "Sync complete: global -> repo"
