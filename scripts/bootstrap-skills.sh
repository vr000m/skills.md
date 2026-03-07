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
	local global_guidelines_code="$GLOBAL_CODEX_SKILLS_DIR/content-review/references/content-guidelines.md"
	local global_guidelines_claude="$GLOBAL_CLAUDE_SKILLS_DIR/content-review/references/content-guidelines.md"

	mkdir -p "$(dirname "$global_guidelines_code")" "$(dirname "$global_guidelines_claude")"
	cp "$repo_guidelines_code" "$global_guidelines_code"
	cp "$repo_guidelines_code" "$global_guidelines_claude"
	echo "Copied canonical repo content-guidelines.md to global skill directories"
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

REPO_CLAUDE_MD="$ROOT_DIR/.claude/CLAUDE.md"
if [[ -f "$REPO_CLAUDE_MD" ]]; then
	mkdir -p "$(dirname "$GLOBAL_CLAUDE_MD")"
	if [[ "$force_overwrite" -eq 0 && -f "$GLOBAL_CLAUDE_MD" ]]; then
		echo "skip: $GLOBAL_CLAUDE_MD already exists (use --force to overwrite)"
	else
		cp "$REPO_CLAUDE_MD" "$GLOBAL_CLAUDE_MD"
		echo "Installed CLAUDE.md: $REPO_CLAUDE_MD -> $GLOBAL_CLAUDE_MD"
	fi
else
	echo "warn: repo CLAUDE.md not found at $REPO_CLAUDE_MD, skipping" >&2
fi

REPO_CODEX_AGENTS="$ROOT_DIR/.codex/AGENTS.md"
if [[ -f "$REPO_CODEX_AGENTS" ]]; then
	mkdir -p "$(dirname "$GLOBAL_CODEX_AGENTS")"
	if [[ "$force_overwrite" -eq 0 && -f "$GLOBAL_CODEX_AGENTS" ]]; then
		echo "skip: $GLOBAL_CODEX_AGENTS already exists (use --force to overwrite)"
	else
		cp "$REPO_CODEX_AGENTS" "$GLOBAL_CODEX_AGENTS"
		echo "Installed AGENTS.md: $REPO_CODEX_AGENTS -> $GLOBAL_CODEX_AGENTS"
	fi
else
	echo "warn: repo AGENTS.md not found at $REPO_CODEX_AGENTS, skipping" >&2
fi

echo "Bootstrap complete: repo -> global (non-destructive by default)"
