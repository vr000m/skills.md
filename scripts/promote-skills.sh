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

if [[ "${1:-}" != "--yes" ]]; then
	echo "error: promotion is destructive; rerun with --yes" >&2
	exit 1
fi

for skill in $MANAGED_SKILLS; do
	mkdir -p "$GLOBAL_CODEX_SKILLS_DIR/$skill" "$GLOBAL_CLAUDE_SKILLS_DIR/$skill"
	rsync -a --delete "$ROOT_DIR/.codex/skills/$skill/" "$GLOBAL_CODEX_SKILLS_DIR/$skill/"
	rsync -a --delete "$ROOT_DIR/.claude/skills/$skill/" "$GLOBAL_CLAUDE_SKILLS_DIR/$skill/"
done

echo "Promotion complete: repo -> global"
