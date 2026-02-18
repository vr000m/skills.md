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
	if [[ -n "$CONTENT_GUIDELINES_LOCAL" && -f "$CONTENT_GUIDELINES_LOCAL" ]]; then
		if ! cmp -s "$CONTENT_GUIDELINES_LOCAL" "$ROOT_DIR/.codex/skills/content-review/references/content-guidelines.md"; then
			echo "drift: codex content-guidelines.md is not authoritative"
			GUIDE_DIFF=1
		fi
		if ! cmp -s "$CONTENT_GUIDELINES_LOCAL" "$ROOT_DIR/.claude/skills/content-review/references/content-guidelines.md"; then
			echo "drift: claude content-guidelines.md is not authoritative"
			GUIDE_DIFF=1
		fi
	elif [[ -n "$CONTENT_GUIDELINES_URL" ]]; then
		guidelines_remote="$(curl -fsSL "$CONTENT_GUIDELINES_URL")"
		if ! cmp -s <(printf '%s' "$guidelines_remote") "$ROOT_DIR/.codex/skills/content-review/references/content-guidelines.md"; then
			echo "drift: codex content-guidelines.md is not authoritative"
			GUIDE_DIFF=1
		fi
		if ! cmp -s <(printf '%s' "$guidelines_remote") "$ROOT_DIR/.claude/skills/content-review/references/content-guidelines.md"; then
			echo "drift: claude content-guidelines.md is not authoritative"
			GUIDE_DIFF=1
		fi
	else
		echo "error: no content guidelines source configured"
		exit 1
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

if [[ "$CODEX_DIFF" -eq 1 || "$CLAUDE_DIFF" -eq 1 || "$GUIDE_DIFF" -eq 1 || "$CLAUDE_MD_DIFF" -eq 1 ]]; then
	echo "check-sync failed"
	exit 1
fi

echo "check-sync passed"
