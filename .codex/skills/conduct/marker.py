"""Review-marker helpers for the conduct skill.

The review marker is a single trailing comment line:

    <!-- reviewed: YYYY-MM-DD @ <sha1> -->

Only the **final non-empty line** of the plan counts — marker-shaped text
elsewhere in the plan (in prose or code fences) is ignored. The hash is
``git hash-object`` of the plan with that final line stripped, so hashing is
idempotent across append-or-replace updates and safe when the plan body
contains illustrative marker-shaped lines.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

MARKER_RE = re.compile(
    r"^<!-- reviewed: (\d{4}-\d{2}-\d{2}) @ ([0-9a-f]{40}) -->\s*$"
)


def strip_marker_for_hashing(plan_text: str) -> str:
    """Return the plan text with its final line removed iff that line matches
    the marker regex. Trailing newline-only whitespace is preserved; intermediate
    marker-shaped lines are left untouched.
    """
    if not plan_text:
        return plan_text
    # Work by lines; a trailing newline produces an empty final element.
    has_trailing_newline = plan_text.endswith("\n")
    lines = plan_text.splitlines()
    # Find the last non-empty line.
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            last_idx = i
            break
    else:
        return plan_text  # all blank

    if MARKER_RE.match(lines[last_idx]):
        remaining = lines[:last_idx]
        # Drop trailing blanks that followed the stripped marker; keep the
        # result consistent regardless of whether the marker had blank lines
        # after it.
        while remaining and not remaining[-1].strip():
            remaining.pop()
        result = "\n".join(remaining)
        if remaining and has_trailing_newline:
            result += "\n"
        return result
    return plan_text


def compute_plan_hash(plan_path: str | Path) -> str:
    """Return ``git hash-object`` of the plan with marker stripped per the rule
    above. Uses a tempfile so the computation is deterministic and does not
    require staging.
    """
    plan = Path(plan_path).read_text()
    stripped = strip_marker_for_hashing(plan)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, suffix=".plan", encoding="utf-8"
    ) as tmp:
        tmp.write(stripped)
        tmp_path = tmp.name
    try:
        out = subprocess.check_output(
            ["git", "hash-object", tmp_path], text=True
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return out.strip()


def read_marker(plan_path: str | Path) -> tuple[str, str] | None:
    """Return ``(iso_date, sha1)`` if the plan's final non-empty line is a
    marker, else ``None``.
    """
    plan = Path(plan_path).read_text().splitlines()
    for line in reversed(plan):
        if not line.strip():
            continue
        match = MARKER_RE.match(line)
        if match:
            return match.group(1), match.group(2)
        return None
    return None


def write_marker(plan_path: str | Path, when: date | None = None) -> str:
    """Append or replace the marker footer. Returns the new sha1.

    Idempotent: running this repeatedly on an unchanged plan yields the same
    marker (same hash, possibly newer date).
    """
    path = Path(plan_path)
    plan = path.read_text()
    stripped = strip_marker_for_hashing(plan)
    # Hash the stripped content — this is what the marker records.
    with tempfile.NamedTemporaryFile(
        "w", delete=False, suffix=".plan", encoding="utf-8"
    ) as tmp:
        tmp.write(stripped)
        tmp_path = tmp.name
    try:
        sha = subprocess.check_output(
            ["git", "hash-object", tmp_path], text=True
        ).strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    iso = (when or date.today()).isoformat()
    marker_line = f"<!-- reviewed: {iso} @ {sha} -->"

    if stripped.endswith("\n") or not stripped:
        new_text = f"{stripped}{marker_line}\n"
    else:
        new_text = f"{stripped}\n{marker_line}\n"
    path.write_text(new_text)
    return sha


def marker_is_stale(plan_path: str | Path) -> bool | None:
    """Return True if the plan has a marker whose hash no longer matches,
    False if the marker is valid, and None if there is no marker at all.
    """
    marker = read_marker(plan_path)
    if marker is None:
        return None
    _, recorded_sha = marker
    current_sha = compute_plan_hash(plan_path)
    return current_sha != recorded_sha
