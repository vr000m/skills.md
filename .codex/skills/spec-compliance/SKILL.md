---
name: spec-compliance
description: "Check whether code complies with a referenced specification section. Trigger when the user asks to 'check compliance', 'verify against spec', 'does this implement RFC X', 'conformance check', 'check against W3C', or references RFC 2119 requirements (MUST/SHOULD/MAY) in the context of code review."
argument-hint: "[file-path] [spec-reference] [section]"
---

# Spec Compliance Check

Given code and a specification reference, fetch the spec section, extract normative requirements (RFC 2119: MUST, SHOULD, MAY), and map each requirement against the code. Return a structured compliance report.

Supports IETF RFCs, IETF Internet-Drafts, W3C specifications, WHATWG specs, and any publicly accessible standards document.

## Usage

- `/spec-compliance src/nack.py RFC 4585 Section 6.2.1` - Check code against an RFC section
- `/spec-compliance src/peer.js "W3C WebRTC 1.0" Section 4.4.1` - Check against a W3C spec
- `/spec-compliance src/quic.rs https://www.rfc-editor.org/rfc/rfc9000#section-17.2` - Check against a direct URL
- `/spec-compliance src/handler.go draft-ietf-httpbis-message-signatures Section 3` - Check against an IETF draft

## Step 1: Parse the Input

Identify two things from the user's request:

1. **Code source** - a file path, line range, or inline code snippet
2. **Spec reference** - one of:
   - RFC number + optional section (for example, `RFC 4585 Section 6.2.1`)
   - IETF draft name + optional section (for example, `draft-ietf-rmcat-gcc Section 5`)
   - W3C/WHATWG spec name + optional section (for example, `W3C WebRTC 1.0 Section 4.4.1`)
   - Direct URL to a spec section

If the section is not specified, ask the user which section to check. Full-spec compliance is too broad to be useful.

If the code path is not specified, ask the user to provide it.

## Step 2: Resolve the Spec

Map the reference to a fetchable URL:

| Reference Format | Resolution |
|---|---|
| `RFC XXXX` | `https://www.rfc-editor.org/rfc/rfcXXXX` |
| `RFC XXXX Section X.Y` | `https://www.rfc-editor.org/rfc/rfcXXXX#section-X.Y` |
| `draft-*` | `https://datatracker.ietf.org/doc/<draft-name>/` then inspect the official page for the current draft/RFC state |
| W3C spec name | Use `search_query` with `domains: ["w3.org"]` to find the official spec URL |
| WHATWG spec name | Use `search_query` with `domains: ["whatwg.org", "spec.whatwg.org"]` to find the official spec URL |
| Direct URL | Use as-is |

Use `search_query` to resolve named specs on official domains only. Use `open` to load the resolved page. If the user provided a section, prefer a URL with the section anchor; if the anchor does not land cleanly, use `find` on the section heading or number.

If the spec or section cannot be found, tell the user and suggest alternatives. Do not proceed with guessed content.

## Step 3: Fetch and Extract Requirements

Load the spec section via `open`. Extract normative statements by identifying RFC 2119 keywords as defined in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174):

- **MUST** / **MUST NOT** / **REQUIRED** / **SHALL** / **SHALL NOT** - absolute requirements
- **SHOULD** / **SHOULD NOT** / **RECOMMENDED** - strong recommendations with justified exceptions
- **MAY** / **OPTIONAL** - truly optional

Per RFC 8174, these keywords only have normative meaning when they appear in ALL CAPITALS. Lowercase `must`, `should`, and `may` are normal English and should be ignored.

For W3C/WHATWG specs that use their own conformance language (for example, `User agents MUST`), apply the same extraction approach and focus on capitalised conformance keywords.

List each extracted requirement with a short identifier for use in the report.

If the section contains no normative language, report that finding and suggest checking adjacent sections or the parent section.

## Step 4: Analyse Code

Read the code from the workspace directly. Use `rg` to find relevant patterns (function names, constants, conditionals) and `nl -ba` or `sed -n` to capture exact line-number evidence.

For each extracted requirement:

1. Search the code for evidence that the requirement is implemented
2. Look for relevant control flow, validation, constants, comments, and tests
3. Classify each requirement:
   - **Met** - code clearly implements the requirement; cite the line(s)
   - **Missing** - no evidence the requirement is addressed
   - **Partial** - requirement is partly addressed but incomplete; explain the gap
   - **N/A** - requirement does not apply to this code's role (for example, a sender-side requirement checked against receiver code)

When classifying, be conservative. If you are uncertain whether code meets a requirement, mark it as **Partial** with an explanation rather than **Met**.

## Step 5: Return the Report

```markdown
## Spec Compliance Report

**Code**: `path/to/file.ext` (lines X-Y)
**Spec**: RFC XXXX, Section X.Y - "Section Title"
**Source**: [link to spec section]
**Requirements found**: N total (X MUST, Y SHOULD, Z MAY)

### MUST Requirements

1. **Met** - "MUST do X"
   Evidence: line 42 - `relevant_code_here`

2. **Missing** - "MUST NOT do Y"
   No handling found for this case in the code.

3. **Partial** - "MUST include Z"
   Line 58 constructs Z but does not handle the edge case described in the spec.

### SHOULD Requirements

1. **Met** - "SHOULD do A"
   Evidence: line 73 - `relevant_code_here`

### MAY Requirements

1. **N/A** - "MAY support B"
   This is a receiver-side requirement; the code implements the sender.

### Summary

| Level | Met | Missing | Partial | N/A | Total |
|-------|-----|---------|---------|-----|-------|
| MUST  |   X |       X |       X |   X |     X |
| SHOULD|   X |       X |       X |   X |     X |
| MAY   |   X |       X |       X |   X |     X |
```

### Report Rules

- Quote only the specific normative statement being checked. Do not reproduce surrounding spec text.
- Always include line-number evidence for Met and Partial findings.
- Group by requirement level (MUST first, then SHOULD, then MAY).
- Include the summary table for quick scanning.
- Link to the spec section so the user can read the full context.

### What NOT to Do

- Do NOT reproduce large blocks of spec text. Quote only the normative statement.
- Do NOT mark a requirement as Met unless you can cite specific code evidence.
- Do NOT skip SHOULD/MAY requirements. They matter for interoperability even if not mandatory.
- Do NOT guess what the spec says. Always fetch and verify.
- Do NOT attempt full-spec compliance without a section reference. Ask the user to narrow scope.

## Edge Cases

- **Spec section not found**: Report the error, suggest checking the section number or searching for the topic. Offer to use `rfc-finder` to locate the right document.
- **No normative language in section**: Report that no RFC 2119 keywords were found. Suggest checking the parent section or a different section.
- **Code file too large**: Ask the user for a line range or function name to narrow the scope.
- **Multiple spec sections**: If the user references multiple sections, check each one separately with its own report section.
- **Ambiguous spec reference**: If the reference could match multiple specs, list the candidates and ask the user to clarify.
- **Non-English specs**: This skill only handles English-language specifications.

## Examples

**User**: `/spec-compliance src/rtcp/nack.rs RFC 4585 Section 6.2.1`

**Response**:

## Spec Compliance Report

**Code**: `src/rtcp/nack.rs` (lines 1-95)
**Spec**: RFC 4585, Section 6.2.1 - "Generic NACK"
**Source**: [RFC 4585 Section 6.2.1](https://www.rfc-editor.org/rfc/rfc4585#section-6.2.1)
**Requirements found**: 4 total (3 MUST, 1 SHOULD)

### MUST Requirements

1. **Met** - "MUST set PT=RTPFB and FMT=1"
   Evidence: line 34 - `header.pt = PT_RTPFB; header.fmt = 1;`

2. **Met** - "The FCI field MUST contain at least one and MAY contain more than one Generic NACK"
   Evidence: line 52 - `assert!(!nack_list.is_empty());`

3. **Partial** - "MUST NOT send a Generic NACK for packets not yet expected"
   Line 61 checks `seq < max_seq` but does not account for sequence number wrapping at 2^16.

### SHOULD Requirements

1. **Missing** - "SHOULD be used in conjunction with the retransmission payload format (RFC 4588)"
   No RFC 4588 retransmission handling found in this file or adjacent modules.

### Summary

| Level | Met | Missing | Partial | N/A | Total |
|-------|-----|---------|---------|-----|-------|
| MUST  |   2 |       0 |       1 |   0 |     3 |
| SHOULD|   0 |       1 |       0 |   0 |     1 |
| MAY   |   0 |       0 |       0 |   0 |     0 |
