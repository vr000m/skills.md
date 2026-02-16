#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
	# shellcheck disable=SC1091
	source "$ROOT_DIR/.env"
fi

GLOBAL_CODEX_SKILLS_DIR="${GLOBAL_CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
GLOBAL_CLAUDE_SKILLS_DIR="${GLOBAL_CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MANAGED_SKILLS="${MANAGED_SKILLS:-content-draft content-review dev-plan fan-out}"
CONTENT_GUIDELINES_LOCAL="${CONTENT_GUIDELINES_LOCAL:-}"
CONTENT_GUIDELINES_URL="${CONTENT_GUIDELINES_URL:-https://raw.githubusercontent.com/vr000m/varunsingh.net/main/.claude/content-guidelines.md}"

REPO_CODEX_DIR="$ROOT_DIR/.codex/skills"
REPO_CLAUDE_DIR="$ROOT_DIR/.claude/skills"

require_dir() {
	local path="$1"
	local name="$2"
	if [[ ! -d "$path" ]]; then
		echo "error: missing $name at $path" >&2
		exit 1
	fi
}

copy_guidelines() {
	local repo_guidelines_code="$REPO_CODEX_DIR/content-review/references/content-guidelines.md"
	local repo_guidelines_claude="$REPO_CLAUDE_DIR/content-review/references/content-guidelines.md"

	if [[ -n "$CONTENT_GUIDELINES_LOCAL" && -f "$CONTENT_GUIDELINES_LOCAL" ]]; then
		cp "$CONTENT_GUIDELINES_LOCAL" "$repo_guidelines_code"
		cp "$CONTENT_GUIDELINES_LOCAL" "$repo_guidelines_claude"
		echo "Using local content guidelines: $CONTENT_GUIDELINES_LOCAL"
	elif [[ -n "$CONTENT_GUIDELINES_URL" ]]; then
		if command -v curl >/dev/null 2>&1; then
			if curl -fsSL "$CONTENT_GUIDELINES_URL" |
				tee "$repo_guidelines_code" >"$repo_guidelines_claude"; then
				echo "Fetched content guidelines from URL"
			else
				echo "warn: failed to fetch CONTENT_GUIDELINES_URL, keeping repo content-guidelines copy" >&2
			fi
		else
			echo "warn: curl is not available, keeping repo content-guidelines copy" >&2
		fi
	else
		echo "warn: no content guidelines source configured, keeping repo content-guidelines copy" >&2
	fi
}

sync_skill() {
	local source_root="$1"
	local target_root="$2"
	local skill="$3"
	local source_dir="$source_root/$skill"
	local target_dir="$target_root/$skill"

	require_dir "$source_dir" "managed skill '$skill' in $source_root"
	mkdir -p "$target_dir"
	rsync -a --delete "$source_dir/" "$target_dir/"
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
	copy_guidelines
fi

echo "Sync complete: global -> repo"
