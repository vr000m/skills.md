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

CODEX_DIFF=0
CLAUDE_DIFF=0
GUIDE_DIFF=0

read -r -a managed_skills <<<"$MANAGED_SKILLS"
for skill in "${managed_skills[@]}"; do
	if ! diff -ru --exclude='content-guidelines.md' "$GLOBAL_CODEX_SKILLS_DIR/$skill" "$ROOT_DIR/.codex/skills/$skill" >/dev/null; then
		echo "drift: .codex/skills/$skill differs from global authority"
		CODEX_DIFF=1
	fi

	if ! diff -ru --exclude='content-guidelines.md' "$GLOBAL_CLAUDE_SKILLS_DIR/$skill" "$ROOT_DIR/.claude/skills/$skill" >/dev/null; then
		echo "drift: .claude/skills/$skill differs from global authority"
		CLAUDE_DIFF=1
	fi
done

if [[ " $MANAGED_SKILLS " == *" content-review "* ]]; then
	CANONICAL_GUIDELINES="$ROOT_DIR/.codex/skills/content-review/references/content-guidelines.md"
	REPO_CLAUDE_GUIDELINES="$ROOT_DIR/.claude/skills/content-review/references/content-guidelines.md"
	GLOBAL_CODEX_GUIDELINES="$GLOBAL_CODEX_SKILLS_DIR/content-review/references/content-guidelines.md"
	GLOBAL_CLAUDE_GUIDELINES="$GLOBAL_CLAUDE_SKILLS_DIR/content-review/references/content-guidelines.md"

	if [[ ! -f "$CANONICAL_GUIDELINES" ]]; then
		echo "drift: missing canonical repo content-guidelines.md at $CANONICAL_GUIDELINES"
		GUIDE_DIFF=1
	fi

	if [[ ! -f "$REPO_CLAUDE_GUIDELINES" ]]; then
		echo "drift: missing repo claude content-guidelines.md at $REPO_CLAUDE_GUIDELINES"
		GUIDE_DIFF=1
	fi

	if [[ ! -f "$GLOBAL_CODEX_GUIDELINES" ]]; then
		echo "drift: missing global codex content-guidelines.md at $GLOBAL_CODEX_GUIDELINES"
		GUIDE_DIFF=1
	fi

	if [[ ! -f "$GLOBAL_CLAUDE_GUIDELINES" ]]; then
		echo "drift: missing global claude content-guidelines.md at $GLOBAL_CLAUDE_GUIDELINES"
		GUIDE_DIFF=1
	fi

	if [[ -f "$CANONICAL_GUIDELINES" && -f "$REPO_CLAUDE_GUIDELINES" ]] && ! cmp -s "$CANONICAL_GUIDELINES" "$REPO_CLAUDE_GUIDELINES"; then
		echo "drift: repo claude content-guidelines.md differs from repo canonical copy"
		GUIDE_DIFF=1
	fi

	if [[ -f "$CANONICAL_GUIDELINES" && -f "$GLOBAL_CODEX_GUIDELINES" ]] && ! cmp -s "$CANONICAL_GUIDELINES" "$GLOBAL_CODEX_GUIDELINES"; then
		echo "drift: global codex content-guidelines.md differs from repo canonical copy"
		GUIDE_DIFF=1
	fi

	if [[ -f "$CANONICAL_GUIDELINES" && -f "$GLOBAL_CLAUDE_GUIDELINES" ]] && ! cmp -s "$CANONICAL_GUIDELINES" "$GLOBAL_CLAUDE_GUIDELINES"; then
		echo "drift: global claude content-guidelines.md differs from repo canonical copy"
		GUIDE_DIFF=1
	fi
fi

CLAUDE_MD_DIFF=0
REPO_CLAUDE_MD="$ROOT_DIR/.claude/CLAUDE.md"
if [[ -f "$GLOBAL_CLAUDE_MD" && -f "$REPO_CLAUDE_MD" ]]; then
	if ! cmp -s "$GLOBAL_CLAUDE_MD" "$REPO_CLAUDE_MD"; then
		echo "drift: CLAUDE.md differs between global and repo"
		CLAUDE_MD_DIFF=1
	fi
elif [[ -f "$GLOBAL_CLAUDE_MD" && ! -f "$REPO_CLAUDE_MD" ]]; then
	echo "drift: CLAUDE.md exists globally but not in repo (run just sync-skills)"
	CLAUDE_MD_DIFF=1
elif [[ ! -f "$GLOBAL_CLAUDE_MD" && -f "$REPO_CLAUDE_MD" ]]; then
	echo "drift: CLAUDE.md exists in repo but not globally (run just promote-skills)"
	CLAUDE_MD_DIFF=1
fi

CODEX_AGENTS_DIFF=0
REPO_CODEX_AGENTS="$ROOT_DIR/.codex/AGENTS.md"
if [[ -f "$GLOBAL_CODEX_AGENTS" && -f "$REPO_CODEX_AGENTS" ]]; then
	if ! cmp -s "$GLOBAL_CODEX_AGENTS" "$REPO_CODEX_AGENTS"; then
		echo "drift: AGENTS.md differs between global and repo"
		CODEX_AGENTS_DIFF=1
	fi
elif [[ -f "$GLOBAL_CODEX_AGENTS" && ! -f "$REPO_CODEX_AGENTS" ]]; then
	echo "drift: AGENTS.md exists globally but not in repo (run just sync-skills)"
	CODEX_AGENTS_DIFF=1
elif [[ ! -f "$GLOBAL_CODEX_AGENTS" && -f "$REPO_CODEX_AGENTS" ]]; then
	echo "drift: AGENTS.md exists in repo but not globally (run just promote-skills)"
	CODEX_AGENTS_DIFF=1
fi

if [[ "$CODEX_DIFF" -eq 1 || "$CLAUDE_DIFF" -eq 1 || "$GUIDE_DIFF" -eq 1 || "$CLAUDE_MD_DIFF" -eq 1 || "$CODEX_AGENTS_DIFF" -eq 1 ]]; then
	echo "check-sync failed"
	exit 1
fi

echo "check-sync passed"
