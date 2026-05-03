#!/usr/bin/env bash
# check-prompt-parity.sh
#
# Verify that prompt-contract artefacts (currently `rubric.md`) are
# byte-identical between `.claude/skills/<skill>/` and
# `.codex/skills/<skill>/` for every entry in MANAGED_SKILLS.
#
# Scope: rubric.md only. Lens prompt bodies and finding schema embedded
# inside SKILL.md are not script-checkable and require manual review per
# the dev plan's Phase 6 verification step.
#
# Inputs:
#   MANAGED_SKILLS  whitespace-separated list of skill names. Sourced
#                   from .env if present; falls back to the hardcoded
#                   default below. Comma-separated values are NOT split.
#
# Per-skill behaviour:
#   - neither side has rubric.md   skip (skill ships no rubric)
#   - exactly one side has it      fail (drift)
#   - both sides have it           diff; fail on mismatch
#
# Exit codes: 0 clean, 1 drift detected.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
	# Safelist parser: `source .env` is unsafe (executes arbitrary shell). Only
	# pull the keys this script reads, and only when they look like a plain
	# assignment to a quoted or bare value.
	while IFS= read -r line; do
		case "$line" in
		MANAGED_SKILLS=*) eval "export $line" ;;
		esac
	done < <(grep -E '^(MANAGED_SKILLS)=' "$ROOT_DIR/.env" || true)
fi

MANAGED_SKILLS="${MANAGED_SKILLS:-conduct content-draft content-review deep-review dev-plan fan-out review-plan rfc-finder spec-compliance update-docs}"

PARITY_DIFF=0

read -r -a managed_skills <<<"$MANAGED_SKILLS"
for skill in "${managed_skills[@]}"; do
	# Reject anything that isn't a plain skill name to block path traversal
	# via .env-supplied MANAGED_SKILLS (e.g. "../../etc/passwd").
	if [[ ! "$skill" =~ ^[A-Za-z0-9_-]+$ ]]; then
		echo "drift: invalid skill name in MANAGED_SKILLS: $skill"
		PARITY_DIFF=1
		continue
	fi

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

	if diff_output=$(diff -u "$claude_rubric" "$codex_rubric" 2>&1); then
		: # rubrics match
	else
		diff_rc=$?
		if [[ $diff_rc -eq 1 ]]; then
			echo "drift: $skill rubric.md differs between .claude and .codex"
		else
			echo "error: diff failed for $skill rubric.md (exit $diff_rc)"
		fi
		echo "$diff_output"
		PARITY_DIFF=1
	fi
done

if [[ "$PARITY_DIFF" -eq 1 ]]; then
	echo "check-prompt-parity failed"
	exit 1
fi

echo "check-prompt-parity passed"
