"""Tests for subagent report parsing and schema validation."""

from __future__ import annotations

import textwrap

import pytest

from schema import (
    SchemaError,
    extract_last_json_block,
    parse_report,
    validate_report,
)


def _impl_report(**overrides):
    base = {
        "role": "implementer",
        "phase_position": 0,
        "phase_label": "1",
        "iteration": 0,
        "files_changed": ["src/a.py"],
        "summary": "did the thing",
        "flags": {"blocked": False, "test_contract_mismatch": False},
    }
    base.update(overrides)
    return base


def test_extract_anchors_on_last_block():
    text = textwrap.dedent(
        """\
        Here is the schema for reference:

        ```json
        {"role": "implementer", "phase_position": 0}
        ```

        ...lots of work...

        ```json
        {"role": "implementer", "phase_position": 0, "summary": "real report"}
        ```
        """
    )
    body = extract_last_json_block(text)
    assert "real report" in body
    assert "schema for reference" not in body


def test_extract_raises_when_no_block():
    with pytest.raises(SchemaError, match="no fenced"):
        extract_last_json_block("just prose, no json fence")


def test_validate_implementer_happy_path():
    validate_report(_impl_report(), "implementer")


def test_validate_rejects_role_mismatch():
    with pytest.raises(SchemaError, match="role mismatch"):
        validate_report(_impl_report(role="test-writer"), "implementer")


def test_validate_rejects_missing_required_key():
    obj = _impl_report()
    del obj["summary"]
    with pytest.raises(SchemaError, match="missing required key: 'summary'"):
        validate_report(obj, "implementer")


def test_validate_rejects_wrong_type():
    obj = _impl_report(files_changed="not a list")
    with pytest.raises(SchemaError, match="files_changed.*expected list, got str"):
        validate_report(obj, "implementer")


def test_validate_allows_extra_keys():
    obj = _impl_report(future_field="ok")
    validate_report(obj, "implementer")


def test_parse_report_round_trip_implementer():
    text = textwrap.dedent(
        """\
        narrative...

        ```json
        {
          "role": "implementer",
          "phase_position": 2,
          "phase_label": "3a",
          "iteration": 1,
          "files_changed": ["src/x.py"],
          "summary": "ok",
          "flags": {}
        }
        ```
        """
    )
    obj = parse_report(text, "implementer")
    assert obj["phase_label"] == "3a"
    assert obj["iteration"] == 1


def test_parse_report_invalid_json_raises():
    text = "```json\n{not valid json}\n```"
    with pytest.raises(SchemaError, match="did not parse"):
        parse_report(text, "implementer")


def test_parse_report_test_writer_required_keys():
    text = textwrap.dedent(
        """\
        ```json
        {
          "role": "test-writer",
          "phase_position": 0,
          "phase_label": "1",
          "iteration": 0,
          "test_files_added": [],
          "test_commands": [],
          "coverage_summary": "none",
          "flags": {}
        }
        ```
        """
    )
    obj = parse_report(text, "test-writer")
    assert obj["role"] == "test-writer"


def test_parse_report_unknown_role_raises():
    with pytest.raises(SchemaError, match="unknown expected_role"):
        parse_report("```json\n{}\n```", "narrator")
