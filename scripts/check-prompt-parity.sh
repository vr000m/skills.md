#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
	# shellcheck disable=SC1091
	source "$ROOT_DIR/.env"
fi

MANAGED_SKILLS="${MANAGED_SKILLS:-conduct content-draft content-review deep-review dev-plan fan-out review-plan rfc-finder spec-compliance update-docs}"

PARITY_DIFF=0

read -r -a managed_skills <<<"$MANAGED_SKILLS"
for skill in "${managed_skills[@]}"; do
	claude_rubric="$ROOT_DIR/.claude/skills/$skill/rubric.md"
	codex_rubric="$ROOT_DIR/.codex/skills/$skill/rubric.md"

	if [[ ! -f "$claude_rubric" && ! -f "$codex_rubric" ]]; then
		# Skill ships no rubric on either side — nothing to compare.
		continue
	fi

	if [[ -f "$claude_rubric" && ! -f "$codex_rubric" ]]; then
		echo "drift: $skill has .claude rubric but no .codex rubric"
		PARITY_DIFF=1
		continue
	fi

	if [[ ! -f "$claude_rubric" && -f "$codex_rubric" ]]; then
		echo "drift: $skill has .codex rubric but no .claude rubric"
		PARITY_DIFF=1
		continue
	fi

	if ! diff -u "$claude_rubric" "$codex_rubric" >/dev/null; then
		echo "drift: $skill rubric.md differs between .claude and .codex"
		diff -u "$claude_rubric" "$codex_rubric" || true
		PARITY_DIFF=1
	fi
done

if [[ "$PARITY_DIFF" -eq 1 ]]; then
	echo "check-prompt-parity failed"
	exit 1
fi

echo "check-prompt-parity passed"
