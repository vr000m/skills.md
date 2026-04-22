"""Subagent report parsing and validation.

Anchors on the LAST fenced ```json block in the subagent's output (the schema
example earlier in the prompt would otherwise capture the first match), parses
it, and validates against the role-specific schema. Pure stdlib — no jsonschema
dependency.

Validation rules are deliberately narrow: they catch the failure modes that
caused real conductor breakage (missing keys, wrong types, role mismatch) and
ignore extra keys, since prompts may evolve faster than the schema.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Matches a fenced ```json block. Non-greedy body so adjacent blocks parse
# independently. We use re.findall + take the last match for "anchor on LAST".
_JSON_FENCE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class SchemaError(ValueError):
    """Raised when a subagent report is missing, unparseable, or invalid."""


_COMMON_REQUIRED = {
    "role": str,
    "phase_position": int,
    "phase_label": str,
    "flags": dict,
}

_ROLE_REQUIRED: dict[str, dict[str, type | tuple[type, ...]]] = {
    "implementer": {
        **_COMMON_REQUIRED,
        "iteration": int,
        "files_changed": list,
        "summary": str,
    },
    "test-writer": {
        **_COMMON_REQUIRED,
        "iteration": int,
        "test_files_added": list,
        "test_commands": list,
        "coverage_summary": str,
    },
    "reviewer": {
        **_COMMON_REQUIRED,
        "findings": list,
    },
}


def extract_last_json_block(text: str) -> str:
    """Return the body of the LAST fenced ```json block in ``text``.

    Raises SchemaError if no such block exists.
    """
    matches = _JSON_FENCE_RE.findall(text)
    if not matches:
        raise SchemaError("no fenced ```json block found in subagent output")
    return matches[-1]


def parse_report(text: str, expected_role: str) -> dict[str, Any]:
    """Extract → parse → validate the terminal JSON report.

    Raises SchemaError with a human-readable message on any failure. The
    conductor catches SchemaError, records the role + raw tail in state, sets
    ``status = "schema_error"``, and hands back to the user (no respawn).
    """
    body = extract_last_json_block(text)
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"final ```json block did not parse: {exc.msg} at line {exc.lineno}") from exc
    if not isinstance(obj, dict):
        raise SchemaError(f"report must be a JSON object, got {type(obj).__name__}")
    validate_report(obj, expected_role)
    return obj


def validate_report(obj: dict[str, Any], expected_role: str) -> None:
    """Validate ``obj`` against the schema for ``expected_role``.

    Checks presence and type of required keys, plus role match. Extra keys are
    allowed so prompts can evolve without breaking older conductors. Raises
    SchemaError on any violation.
    """
    if expected_role not in _ROLE_REQUIRED:
        raise SchemaError(f"unknown expected_role: {expected_role!r}")
    role_field = obj.get("role")
    if role_field != expected_role:
        raise SchemaError(
            f"role mismatch: expected {expected_role!r}, got {role_field!r}"
        )
    schema = _ROLE_REQUIRED[expected_role]
    for key, expected_type in schema.items():
        if key not in obj:
            raise SchemaError(f"missing required key: {key!r}")
        if not isinstance(obj[key], expected_type):
            actual = type(obj[key]).__name__
            want = (
                expected_type.__name__
                if isinstance(expected_type, type)
                else " or ".join(t.__name__ for t in expected_type)
            )
            raise SchemaError(
                f"key {key!r} has wrong type: expected {want}, got {actual}"
            )
