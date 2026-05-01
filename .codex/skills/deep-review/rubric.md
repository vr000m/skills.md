# Deep Review Output Rubric

Gradeable criteria for evaluating a completed deep-review report. Doubles as a local self-check
before presenting findings to the user.

## Coverage

- Every enabled lens produced findings or an explicit "no issues" statement
- The Spec lens ran iff the dev-plan `## Review Focus` section listed RFCs or specs (skip is
  justified otherwise)
- Lenses that timed out or errored are reported as `timed_out` / `errored`, not silently dropped
- Findings are deduplicated across lenses (same file:line collapsed to highest severity, overlap
  noted)

## Finding Quality

- Each finding has all five fields: Severity, Category, Location (file:line), Evidence, Suggestion
- Severity is one of Critical / Important / Minor - no other values
- Category matches the lens that produced it (Logic, Security, Spec, Architecture, Documentation)
- Evidence cites concrete code, diff hunk, or spec section - not a paraphrase
- Suggestion is a specific, actionable change - not "consider improving X"

## Suppression Discipline

- Suppression is sourced from the merge-base `AGENTS.md ## Review Checklist`, not the current branch
- Suppressed findings name the specific file, symbol, or pattern matched, not just the category
- Findings are not generalised beyond what the checklist actually states

## Scope Discipline

- Each lens stays inside its scope (Logic doesn't flag style; Security doesn't flag docs)
- The Spec lens does not invent specs beyond what `## Review Focus` lists
- No finding is manufactured to fill a slot - clean lenses say so explicitly

## Output Structure

- Report is grouped by severity (Critical -> Important -> Minor)
- One-line overall summary at the top
- Skipped or timed-out lenses are called out under residual risks
- Markdown is well-formed and renders cleanly

## Continuation Safety

- If `--continue` was used and stored `head_commit == HEAD`, only `timed_out` or `errored` lenses
  were re-run; completed lens findings were reused
- If `--continue` was used and `HEAD` advanced past the stored `head_commit`, all lenses re-ran over
  the new range only and the report uses the continuation format with the `(continuation)` header,
  an explicit "Range reviewed this run" line, and prior findings listed separately under
  "Prior findings ... - verify these are addressed"
- If stored `head_commit` is not an ancestor of `HEAD`, or `review_focus_hash` changed, the run fell
  back to `--full` with a warning
- Stored state in `.deep-review/latest.json` matches the schema version
