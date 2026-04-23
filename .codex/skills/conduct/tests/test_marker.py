"""Tests for review-marker hashing and writing.

Covers final-line-only strip semantics (marker-shaped lines in body must NOT
be stripped), hash idempotency across append-or-replace, and staleness
detection after a body edit.

Runs ``git hash-object`` via subprocess; skips if git is not available.
"""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from marker import (
    MARKER_RE,
    compute_plan_hash,
    marker_is_stale,
    read_marker,
    strip_marker_for_hashing,
    write_marker,
)


requires_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git not available"
)


def test_marker_regex_accepts_valid():
    assert MARKER_RE.match(
        "<!-- reviewed: 2026-04-22 @ 0123456789abcdef0123456789abcdef01234567 -->"
    )


def test_marker_regex_rejects_short_hash():
    assert not MARKER_RE.match("<!-- reviewed: 2026-04-22 @ 0123 -->")


def test_strip_leaves_body_marker_shaped_text_alone():
    plan = textwrap.dedent(
        """\
        # Plan

        Here is an example: `<!-- reviewed: 2026-04-22 @ {} -->`.

        And in a fence:

            <!-- reviewed: 2026-04-22 @ {} -->

        More body.
        """
    ).format("a" * 40, "b" * 40)
    assert strip_marker_for_hashing(plan) == plan


def test_strip_removes_trailing_marker_and_trailing_blanks():
    body = "# Plan\n\nsome text\n"
    marker = "<!-- reviewed: 2026-04-22 @ " + "c" * 40 + " -->"
    plan = body + marker + "\n\n"
    stripped = strip_marker_for_hashing(plan)
    assert stripped == body


@requires_git
def test_write_marker_idempotent_on_unchanged_plan(tmp_path: Path):
    plan_path = tmp_path / "plan.md"
    plan_path.write_text("# Plan\n\nbody\n")
    sha1 = write_marker(plan_path)
    sha2 = write_marker(plan_path)
    assert sha1 == sha2
    # Running twice must not stack markers — the final-line check gives one.
    lines = plan_path.read_text().splitlines()
    assert sum(1 for line in lines if MARKER_RE.match(line)) == 1


@requires_git
def test_write_marker_updates_hash_when_body_changes(tmp_path: Path):
    plan_path = tmp_path / "plan.md"
    plan_path.write_text("# Plan\n\nbody v1\n")
    first = write_marker(plan_path)

    text = plan_path.read_text()
    # Mutate body but keep marker at end.
    lines = text.splitlines()
    lines[2] = "body v2"
    plan_path.write_text("\n".join(lines) + "\n")

    assert marker_is_stale(plan_path) is True
    second = write_marker(plan_path)
    assert first != second
    assert marker_is_stale(plan_path) is False


@requires_git
def test_read_marker_ignores_body_examples(tmp_path: Path):
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        textwrap.dedent(
            f"""\
            # Plan

            Example in prose: `<!-- reviewed: 2020-01-01 @ {'d' * 40} -->`.
            """
        )
    )
    assert read_marker(plan_path) is None
    # Add a real marker; verify the reader picks the real one.
    sha = write_marker(plan_path)
    date_sha = read_marker(plan_path)
    assert date_sha is not None
    assert date_sha[1] == sha


@requires_git
def test_compute_plan_hash_matches_git_hash_object(tmp_path: Path):
    plan_path = tmp_path / "plan.md"
    plan_path.write_text("# Plan\n\nbody\n")
    expected = subprocess.check_output(
        ["git", "hash-object", str(plan_path)], text=True
    ).strip()
    assert compute_plan_hash(plan_path) == expected
