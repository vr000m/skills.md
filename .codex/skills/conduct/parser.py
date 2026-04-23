"""Plan-parsing helpers for the conduct skill.

Pure regex + string munging. No I/O beyond reading plan text that the caller
has already loaded. Mirrors the algorithm documented in SKILL.md so main Codex
can either invoke this module or inline the equivalent logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PHASE_HEADING_RE = re.compile(
    r"^###\s+Phase\s+(\S+)\s*:\s*(.+?)\s*(\([^)]*\))?\s*$"
)

TEST_COMMAND_RE = re.compile(
    r"^\*\*Test command:\*\*\s+`([^`]+)`\s*$"
)

VALIDATION_COMMAND_RE = re.compile(
    r"^\*\*Validation cmd:\*\*\s+`([^`]+)`\s*$"
)

IMPL_FILES_RE = re.compile(r"^\*\*Impl files:\*\*\s+(.+?)\s*$")
TEST_FILES_RE = re.compile(r"^\*\*Test files:\*\*\s+(.+?)\s*$")

CHECKBOX_RE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])\]")

IMPLEMENTATION_CHECKLIST_HEADING = "## Implementation Checklist"


@dataclass
class Phase:
    position: int  # 0-based document order
    label: str  # verbatim from heading (e.g. "3", "3a")
    title: str
    body_lines: list[str] = field(default_factory=list)
    impl_files: list[str] | None = None
    test_files: list[str] | None = None
    test_command: str | None = None
    validation_command: str | None = None
    is_complete: bool = False

    def has_any_slot(self) -> bool:
        """True if this phase declares any conduct contract slot."""
        return bool(
            self.impl_files
            or self.test_files
            or self.test_command
            or self.validation_command
        )


def _split_checklist(plan_text: str) -> list[str]:
    lines = plan_text.splitlines()
    try:
        start = next(
            i
            for i, line in enumerate(lines)
            if line.strip() == IMPLEMENTATION_CHECKLIST_HEADING
        )
    except StopIteration:
        return []
    return lines[start + 1 :]


def parse_phases(plan_text: str) -> list[Phase]:
    """Return phases in document order, with per-phase slot values filled in.

    Phases whose task checkboxes are all ticked (`- [x]`) are marked complete.
    Callers typically filter with ``[p for p in parse_phases(...) if not p.is_complete]``.
    """
    checklist_lines = _split_checklist(plan_text)
    phases: list[Phase] = []
    current: Phase | None = None

    for line in checklist_lines:
        heading = PHASE_HEADING_RE.match(line)
        if heading:
            current = Phase(
                position=len(phases),
                label=heading.group(1),
                title=heading.group(2).strip(),
            )
            phases.append(current)
            continue
        if current is None:
            continue
        # Only a top-level (`## `) section boundary ends the current phase. A
        # new phase heading is already matched above. A non-Phase `### ` line
        # (e.g. a `### Notes` subheading inside the phase body) is absorbed as
        # body content rather than silently dropping the rest of the phase.
        if line.startswith("## "):
            current = None
            continue
        current.body_lines.append(line)

    for phase in phases:
        phase.impl_files = _parse_file_list(phase.body_lines, IMPL_FILES_RE)
        phase.test_files = _parse_file_list(phase.body_lines, TEST_FILES_RE)
        phase.test_command = _parse_backtick_command(phase.body_lines, TEST_COMMAND_RE)
        phase.validation_command = _parse_backtick_command(
            phase.body_lines, VALIDATION_COMMAND_RE
        )
        phase.is_complete = _all_checkboxes_ticked(phase.body_lines)

    return phases


def _parse_file_list(body_lines: list[str], pattern: re.Pattern[str]) -> list[str] | None:
    for line in body_lines:
        match = pattern.match(line)
        if match:
            raw = match.group(1).strip()
            if raw.lower() in {"none", "n/a", "-"}:
                return []
            return [item.strip() for item in raw.split(",") if item.strip()]
    return None


def _parse_backtick_command(
    body_lines: list[str], pattern: re.Pattern[str]
) -> str | None:
    matches = [pattern.match(line) for line in body_lines]
    matches = [m for m in matches if m]
    if not matches:
        return None
    return matches[0].group(1)


def _parse_test_command(body_lines: list[str]) -> str | None:
    """Back-compat alias used by older call sites and tests."""
    return _parse_backtick_command(body_lines, TEST_COMMAND_RE)


def _all_checkboxes_ticked(body_lines: list[str]) -> bool:
    ticked = 0
    total = 0
    for line in body_lines:
        match = CHECKBOX_RE.match(line)
        if not match:
            continue
        total += 1
        if match.group("mark").lower() == "x":
            ticked += 1
    return total > 0 and ticked == total


_GLOB_CHARS = ("*", "?", "[")


def _has_glob(path: str) -> bool:
    return any(ch in path for ch in _GLOB_CHARS)


def files_overlap(impl: list[str] | None, test: list[str] | None) -> bool:
    """Return True if declared impl and test paths could share any file.

    Conservative on globs: if any entry contains ``*``, ``?``, or ``[``, we
    cannot prove disjointness with literal-prefix matching, so we report
    overlap → caller falls back to sequential. Callers wanting precise glob
    expansion should resolve against ``git ls-files`` first and pass the
    materialised list in.

    If either list is missing or empty, returns False (caller decides fallback
    policy — typically 'sequential because missing slot').
    """
    if not impl or not test:
        return False
    if any(_has_glob(p) for p in impl) or any(_has_glob(p) for p in test):
        return True
    impl_set = {path.rstrip("/") for path in impl}
    test_set = {path.rstrip("/") for path in test}
    for a in impl_set:
        for b in test_set:
            if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                return True
    return False
