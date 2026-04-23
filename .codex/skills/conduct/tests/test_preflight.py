"""End-to-end preflight integration tests.

Composes marker check + plan parsing the way SKILL.md describes the conductor's
preflight, on synthetic plans with realistic edge cases:

- no marker → preflight rejects
- stale marker → preflight rejects
- valid marker on the same content → preflight accepts
- marker-shaped lines in the body do NOT cause false-positive marker reads
  (the conductor anchors only on the final non-empty line)
- phase parsing on a plan with completed phases, glob slots, and tricky titles

These cover Phase 6 manual scenarios "Preflight hard stop", "Preflight stale
marker", "Marker-in-body safety", and "Phase parsing" as integration checks
rather than ad-hoc shell invocations.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from conduct.marker import (
    compute_plan_hash,
    marker_is_stale,
    read_marker,
    write_marker,
)
from conduct.parser import files_overlap, parse_phases


def _scratch_plan(tmp_path: Path, body: str) -> Path:
    plan = tmp_path / "20260422-scratch.md"
    plan.write_text(textwrap.dedent(body))
    return plan


PHASE_BODY = """\
# Scratch Plan

Some prose.

## Implementation Checklist

### Phase 1: First thing

**Impl files:** src/a.py
**Test files:** tests/test_a.py
**Test command:** `pytest tests/test_a.py -v`

- [ ] do the thing

### Phase 2: Second (with annotation)

**Impl files:** src/*.py
**Test files:** tests/test_b.py
**Test command:** `pytest -q`

- [ ] do the other thing

### Phase 3: Already done

**Impl files:** src/c.py

- [x] finished
- [x] also finished
"""


def test_preflight_rejects_unmarked_plan(tmp_path):
    plan = _scratch_plan(tmp_path, PHASE_BODY)
    assert read_marker(plan) is None
    assert marker_is_stale(plan) is None  # sentinel "no marker"


def test_preflight_accepts_freshly_marked_plan(tmp_path):
    plan = _scratch_plan(tmp_path, PHASE_BODY)
    sha = write_marker(plan)
    assert read_marker(plan) == (read_marker(plan)[0], sha)
    assert marker_is_stale(plan) is False


def test_preflight_detects_stale_marker(tmp_path):
    plan = _scratch_plan(tmp_path, PHASE_BODY)
    write_marker(plan)
    # Edit the body, not the marker.
    text = plan.read_text()
    plan.write_text(text.replace("First thing", "First thing (edited)"))
    assert marker_is_stale(plan) is True


def test_preflight_marker_in_body_does_not_falsely_validate(tmp_path):
    """Body contains marker-shaped lines (in prose AND inside a fenced block).
    Without a real trailing marker, preflight must report 'no marker' rather
    than picking up the in-body example.
    """
    body = (
        PHASE_BODY
        + textwrap.dedent(
            """

            ## Notes

            Earlier reviews looked like:

                <!-- reviewed: 2025-12-01 @ 0123456789abcdef0123456789abcdef01234567 -->

            ```
            <!-- reviewed: 2025-12-02 @ fedcba9876543210fedcba9876543210fedcba98 -->
            ```
            """
        )
    )
    plan = _scratch_plan(tmp_path, body)
    assert read_marker(plan) is None
    assert marker_is_stale(plan) is None


def test_preflight_marker_after_in_body_examples_is_the_one_that_counts(tmp_path):
    """Same scenario, but with a real trailing marker. The conductor must hash
    against the body (in-body examples included) and accept.
    """
    body = (
        PHASE_BODY
        + textwrap.dedent(
            """

            ## Notes

            Earlier reviews looked like:

                <!-- reviewed: 2025-12-01 @ 0123456789abcdef0123456789abcdef01234567 -->
            """
        )
    )
    plan = _scratch_plan(tmp_path, body)
    write_marker(plan)
    assert marker_is_stale(plan) is False
    iso, sha = read_marker(plan)
    # Sanity: the recorded sha matches the recomputed hash of the stripped body.
    assert sha == compute_plan_hash(plan)


def test_preflight_parses_phases_with_completion_and_glob_slots(tmp_path):
    plan = _scratch_plan(tmp_path, PHASE_BODY)
    phases = parse_phases(plan.read_text())
    labels = [(p.label, p.title, p.is_complete) for p in phases]
    assert labels == [
        ("1", "First thing", False),
        ("2", "Second", False),  # parenthesised annotation stripped
        ("3", "Already done", True),
    ]
    # Glob in phase 2 forces sequential fallback (per the C2 fix in parser.py).
    p2 = phases[1]
    assert files_overlap(p2.impl_files, p2.test_files) is True


def test_preflight_full_composition_happy_path(tmp_path):
    """Simulate what the conductor's preflight does:
    1. Read marker; bail if missing.
    2. Compare against current hash; bail if stale.
    3. Parse phases; pick first non-complete.
    """
    plan = _scratch_plan(tmp_path, PHASE_BODY)
    write_marker(plan)
    assert read_marker(plan) is not None
    assert marker_is_stale(plan) is False
    phases = parse_phases(plan.read_text())
    next_phase = next(p for p in phases if not p.is_complete)
    assert next_phase.label == "1"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t + "\nappended trailing prose\n",
        lambda t: t.replace("Phase 1", "Phase one"),
        lambda t: t.replace("- [ ] do the thing", "- [x] do the thing"),
    ],
)
def test_preflight_any_body_change_invalidates_marker(tmp_path, mutation):
    plan = _scratch_plan(tmp_path, PHASE_BODY)
    write_marker(plan)
    plan.write_text(mutation(plan.read_text()))
    # Either outcome means preflight hard-stops:
    #   - True: marker still present but hash mismatches
    #   - None: mutation displaced the marker from the final line
    # Both produce the same user-facing message ("re-run /review-plan").
    assert marker_is_stale(plan) is not False
