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

confirmed=0
force_overwrite=0
for arg in "$@"; do
	case "$arg" in
	--yes)
		confirmed=1
		;;
	--force)
		force_overwrite=1
		;;
	*)
		echo "error: unknown argument '$arg' (allowed: --yes, --force)" >&2
		exit 1
		;;
	esac
done

if [[ "$confirmed" -ne 1 ]]; then
	echo "error: bootstrap writes global skill dirs; rerun with --yes" >&2
	exit 1
fi

read -r -a managed_skills <<<"$MANAGED_SKILLS"

copy_guidelines_to_global() {
	local repo_guidelines_code="$ROOT_DIR/.codex/skills/content-review/references/content-guidelines.md"
	local repo_guidelines_claude="$ROOT_DIR/.claude/skills/content-review/references/content-guidelines.md"
	local global_guidelines_code="$GLOBAL_CODEX_SKILLS_DIR/content-review/references/content-guidelines.md"
	local global_guidelines_claude="$GLOBAL_CLAUDE_SKILLS_DIR/content-review/references/content-guidelines.md"

	mkdir -p "$(dirname "$global_guidelines_code")" "$(dirname "$global_guidelines_claude")"

	if [[ -n "$CONTENT_GUIDELINES_LOCAL" && -f "$CONTENT_GUIDELINES_LOCAL" ]]; then
		cp "$CONTENT_GUIDELINES_LOCAL" "$global_guidelines_code"
		cp "$CONTENT_GUIDELINES_LOCAL" "$global_guidelines_claude"
		echo "Using local content guidelines: $CONTENT_GUIDELINES_LOCAL"
	elif [[ -n "$CONTENT_GUIDELINES_URL" ]]; then
		if command -v curl >/dev/null 2>&1; then
			if curl -fsSL "$CONTENT_GUIDELINES_URL" |
				tee "$global_guidelines_code" >"$global_guidelines_claude"; then
				echo "Fetched content guidelines from URL"
			else
				cp "$repo_guidelines_code" "$global_guidelines_code"
				cp "$repo_guidelines_claude" "$global_guidelines_claude"
				echo "warn: failed to fetch CONTENT_GUIDELINES_URL, used repo content-guidelines copy" >&2
			fi
		else
			cp "$repo_guidelines_code" "$global_guidelines_code"
			cp "$repo_guidelines_claude" "$global_guidelines_claude"
			echo "warn: curl is not available, used repo content-guidelines copy" >&2
		fi
	else
		cp "$repo_guidelines_code" "$global_guidelines_code"
		cp "$repo_guidelines_claude" "$global_guidelines_claude"
		echo "warn: no content guidelines source configured, used repo content-guidelines copy" >&2
	fi
}

mkdir -p "$GLOBAL_CODEX_SKILLS_DIR" "$GLOBAL_CLAUDE_SKILLS_DIR"
for skill in "${managed_skills[@]}"; do
	mkdir -p "$GLOBAL_CODEX_SKILLS_DIR/$skill" "$GLOBAL_CLAUDE_SKILLS_DIR/$skill"

	if [[ "$force_overwrite" -eq 0 && -n "$(find "$GLOBAL_CODEX_SKILLS_DIR/$skill" -mindepth 1 -print -quit 2>/dev/null)" ]]; then
		echo "skip: $GLOBAL_CODEX_SKILLS_DIR/$skill already has content (use --force to overwrite)"
	else
		rsync -a --delete "$ROOT_DIR/.codex/skills/$skill/" "$GLOBAL_CODEX_SKILLS_DIR/$skill/"
	fi

	if [[ "$force_overwrite" -eq 0 && -n "$(find "$GLOBAL_CLAUDE_SKILLS_DIR/$skill" -mindepth 1 -print -quit 2>/dev/null)" ]]; then
		echo "skip: $GLOBAL_CLAUDE_SKILLS_DIR/$skill already has content (use --force to overwrite)"
	else
		rsync -a --delete "$ROOT_DIR/.claude/skills/$skill/" "$GLOBAL_CLAUDE_SKILLS_DIR/$skill/"
	fi
done

if [[ " $MANAGED_SKILLS " == *" content-review "* ]]; then
	copy_guidelines_to_global
fi

echo "Bootstrap complete: repo -> global (non-destructive by default)"
