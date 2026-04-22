"""In-process conductor implementation of the SKILL.md per-phase algorithm.

This module exists primarily as a deterministic test harness. Real /conduct
runs are driven by main Claude inlining the SKILL.md algorithm with the Agent
tool as the spawn primitive — but that path is impossible to unit-test because
``Agent`` calls cost real budget and produce non-deterministic output.

Here we factor the loop into a function with three injectable seams:

- ``spawn_fn(SpawnRequest) -> str`` — replaces the ``Agent`` tool. Receives a
  request describing what role to spawn and the rendered prompt context;
  returns the raw text the subagent would have printed (must end in a fenced
  ```json block per the schema in implementer-prompt.md / test-writer-prompt.md).
- ``test_runner_fn(cmd, timeout) -> TestResult`` — defaults to ``runner.run_tests``;
  tests can inject scripted results without spawning subprocesses.
- ``lint_check_fn() -> Optional[str]`` — defaults to no-op; tests inject a stub
  that returns a diagnostic string when a pre-existing lint failure is seeded.

The module is intentionally NOT a CLI. SKILL.md is the user-facing contract;
this is the algorithmic core that a human-readable algorithm description and a
LLM-driven harness both target.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from lock import StateLock
from marker import marker_is_stale, read_marker
from parser import Phase, files_overlap, parse_phases
from runner import TestResult, run_tests
from schema import SchemaError, parse_report


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class SpawnRequest:
    """Everything the spawn seam needs to produce a subagent reply.

    Mirrors the placeholders enumerated in the prompt templates, plus a couple
    of fields a stub harness needs for scripted dispatch (role, iteration).
    """

    role: str  # 'implementer' | 'test-writer' | 'reviewer'
    plan_path: str
    phase_position: int
    phase_label: str
    phase_title: str
    iteration: int
    base_sha: str
    prior_diff: str = ""
    test_failures: str = ""
    diff: str = ""  # reviewer only


SpawnFn = Callable[[SpawnRequest], str]
TestRunnerFn = Callable[[str, float], TestResult]
LintCheckFn = Callable[[], Optional[str]]
HandbackFn = Callable[[dict], None]


@dataclass
class ConductOptions:
    plan_path: Path
    repo_root: Path
    spawn: SpawnFn
    test_runner: TestRunnerFn = run_tests
    lint_check: LintCheckFn = lambda: None
    test_cmd_override: Optional[str] = None
    test_timeout: float = 300.0
    max_iterations: int = 3
    resume: bool = False
    on_handback: Optional[HandbackFn] = None


@dataclass
class ConductResult:
    status: str  # 'awaiting_user' | 'blocked' | 'schema_error' | 'complete' | 'preflight_fail'
    state: dict
    summary: str
    next_command: Optional[str] = None
    diagnostic: Optional[str] = None


# ---------------------------------------------------------------------------
# Git helpers (cwd-scoped)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _head_sha(repo_root: Path) -> str:
    return _git(["rev-parse", "HEAD"], repo_root).stdout.strip()


def _staged_diff(repo_root: Path) -> str:
    return _git(["diff", "--cached"], repo_root).stdout


def _reset_index(repo_root: Path) -> None:
    _git(["reset"], repo_root)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def run_preflight(opts: ConductOptions) -> Optional[ConductResult]:
    """Returns None on success, else a ConductResult describing the hard stop."""
    if not opts.plan_path.exists():
        return ConductResult(
            status="preflight_fail",
            state={},
            summary=f"plan not found: {opts.plan_path}",
            diagnostic=f"plan not found: {opts.plan_path}",
        )

    marker = read_marker(opts.plan_path)
    if marker is None:
        return ConductResult(
            status="preflight_fail",
            state={},
            summary="no review marker",
            diagnostic=f"Run: /review-plan {opts.plan_path}",
        )
    stale = marker_is_stale(opts.plan_path)
    if stale is True:
        return ConductResult(
            status="preflight_fail",
            state={},
            summary="stale review marker",
            diagnostic=f"Run: /review-plan {opts.plan_path}",
        )

    lint_diag = opts.lint_check()
    if lint_diag:
        return ConductResult(
            status="preflight_fail",
            state={},
            summary="pre-existing lint failure",
            diagnostic=(
                "Tree has pre-existing lint/hook failures; fix them before running this skill\n"
                + lint_diag
            ),
        )
    return None


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def _state_path(opts: ConductOptions) -> Path:
    return opts.repo_root / ".conduct" / f"state-{opts.plan_path.stem}.json"


def _load_or_init_state(opts: ConductOptions) -> dict:
    sp = _state_path(opts)
    if sp.exists():
        state = json.loads(sp.read_text())
        if opts.resume:
            state["resume_base_sha"] = _head_sha(opts.repo_root)
            state["status"] = "running"
        return state
    return {
        "plan_path": str(opts.plan_path),
        "base_sha": _head_sha(opts.repo_root),
        "phase_index": 0,
        "completed_phases": [],
        "iteration_count": 0,
        "status": "running",
        "blocker": None,
    }


def _persist_state(opts: ConductOptions, state: dict) -> None:
    sp = _state_path(opts)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Per-phase
# ---------------------------------------------------------------------------


def _spawn_strategy(phase: Phase) -> tuple[str, str]:
    """Return ('parallel'|'sequential', reason)."""
    if not phase.impl_files or not phase.test_files:
        return "sequential", "missing slot"
    if files_overlap(phase.impl_files, phase.test_files):
        return "sequential", "file overlap"
    return "parallel", "disjoint paths"


def _resolve_test_cmd(opts: ConductOptions, phase: Phase) -> Optional[str]:
    if opts.test_cmd_override:
        return opts.test_cmd_override
    return phase.test_command


def _phase_baseline(state: dict) -> str:
    """Baseline SHA for the rogue-commit comparison.

    Per SKILL.md Step 8: ``resume_base_sha`` if this run started from --resume,
    otherwise the last completed phase's commit_sha (or base_sha for phase 1).
    """
    if state.get("resume_base_sha"):
        return state["resume_base_sha"]
    completed = state.get("completed_phases") or []
    if completed:
        return completed[-1]["commit_sha"]
    return state["base_sha"]


def _run_phase(
    opts: ConductOptions,
    state: dict,
    phase: Phase,
) -> ConductResult:
    state["iteration_count"] = 0
    state["current_phase_title"] = phase.title
    _persist_state(opts, state)

    strategy, strategy_reason = _spawn_strategy(phase)
    base_sha = _phase_baseline(state)
    test_cmd = _resolve_test_cmd(opts, phase)

    iteration = 0
    prior_diff = ""
    test_failures = ""
    respawn_role = "implementer"  # may flip to test-writer for one iteration

    while True:
        req = SpawnRequest(
            role=respawn_role,
            plan_path=str(opts.plan_path),
            phase_position=phase.position,
            phase_label=phase.label,
            phase_title=phase.title,
            iteration=iteration,
            base_sha=base_sha,
            prior_diff=prior_diff,
            test_failures=test_failures,
        )

        # On the first iteration we may also spawn the test-writer (parallel
        # or sequential per strategy). For fix-loop iterations we only respawn
        # one role per the SKILL.md algorithm.
        impl_text: Optional[str] = None
        test_text: Optional[str] = None

        if iteration == 0:
            impl_text = opts.spawn(req)
            if strategy == "parallel":
                test_req = SpawnRequest(
                    role="test-writer",
                    plan_path=req.plan_path,
                    phase_position=req.phase_position,
                    phase_label=req.phase_label,
                    phase_title=req.phase_title,
                    iteration=0,
                    base_sha=req.base_sha,
                )
                test_text = opts.spawn(test_req)
            else:
                test_req = SpawnRequest(
                    role="test-writer",
                    plan_path=req.plan_path,
                    phase_position=req.phase_position,
                    phase_label=req.phase_label,
                    phase_title=req.phase_title,
                    iteration=0,
                    base_sha=req.base_sha,
                )
                test_text = opts.spawn(test_req)
        else:
            text = opts.spawn(req)
            if respawn_role == "implementer":
                impl_text = text
            else:
                test_text = text

        # Parse reports (every text we got).
        try:
            if impl_text is not None:
                impl_report = parse_report(impl_text, "implementer")
            else:
                impl_report = None
            if test_text is not None:
                test_report = parse_report(test_text, "test-writer")
            else:
                test_report = None
        except SchemaError as exc:
            state["status"] = "schema_error"
            state["blocker"] = str(exc)
            _persist_state(opts, state)
            return ConductResult(
                status="schema_error",
                state=state,
                summary=f"phase {phase.label} schema error: {exc}",
                diagnostic=str(exc),
            )

        # Resolve test command. If absent and no override → skip-with-warning,
        # go straight to commit.
        warnings: list[str] = []
        if test_cmd is None:
            warnings.append("no test command; skipped tests")
            commit_outcome = _commit_phase(opts, state, phase, base_sha, warnings)
            if commit_outcome.status != "running":
                return commit_outcome
            return _handback(opts, state, phase, "skipped", iteration, strategy, strategy_reason, warnings)

        # Step 5: run tests.
        result = opts.test_runner(test_cmd, opts.test_timeout)
        if result.returncode == 0 and not result.timed_out:
            commit_outcome = _commit_phase(opts, state, phase, base_sha, warnings)
            if commit_outcome.status != "running":
                return commit_outcome
            return _handback(opts, state, phase, "passed", iteration, strategy, strategy_reason, warnings)

        # Step 6: fix loop.
        state["iteration_count"] += 1
        _persist_state(opts, state)
        if state["iteration_count"] > opts.max_iterations:
            state["status"] = "blocked"
            state["blocker"] = (
                f"Phase {phase.label} stalled after {opts.max_iterations} iterations"
            )
            _persist_state(opts, state)
            return ConductResult(
                status="blocked",
                state=state,
                summary=state["blocker"],
                diagnostic=result.output[-2000:],
            )

        # Capture staged diff, reset index, then choose respawn role.
        prior_diff = _staged_diff(opts.repo_root)
        _reset_index(opts.repo_root)
        test_failures = result.output

        flag_mismatch = bool(
            impl_report
            and impl_report.get("flags", {}).get("test_contract_mismatch") is True
        )
        respawn_role = "test-writer" if flag_mismatch else "implementer"
        iteration = state["iteration_count"]


def _commit_phase(
    opts: ConductOptions,
    state: dict,
    phase: Phase,
    base_sha: str,
    warnings: list[str],
) -> ConductResult:
    """Step 8: rogue-commit detection + boundary commit.

    Returns ConductResult with status='running' on success (caller continues to
    handback), or a terminal status on rogue/hook failure.
    """
    head_now = _head_sha(opts.repo_root)
    if head_now != base_sha:
        state["status"] = "awaiting_user"
        state["blocker"] = "rogue commit"
        completed = {
            "index": phase.position,
            "label": phase.label,
            "title": phase.title,
            "commit_sha": None,
            "rogue_commit_sha": head_now,
            "tests": "passed-but-rogue",
            "iterations": state["iteration_count"],
        }
        state.setdefault("completed_phases", []).append(completed)
        _persist_state(opts, state)
        return ConductResult(
            status="awaiting_user",
            state=state,
            summary=f"phase {phase.label}: rogue commit {head_now}",
            diagnostic=f"subagent committed {head_now}; conductor refused to stack a second commit",
        )

    # If nothing is staged (skip-tests on a no-op phase), still boundary-commit
    # with --allow-empty? SKILL.md doesn't say; we choose to skip the commit
    # cleanly when there's nothing to commit and warn instead.
    if not _staged_diff(opts.repo_root):
        warnings.append("no staged changes; skipping commit")
        completed = {
            "index": phase.position,
            "label": phase.label,
            "title": phase.title,
            "commit_sha": None,
            "tests": "passed",
            "iterations": state["iteration_count"],
        }
        state.setdefault("completed_phases", []).append(completed)
        return ConductResult(status="running", state=state, summary="")

    commit_msg = f"conduct: phase {phase.label} — {phase.title}"
    proc = _git(["commit", "-m", commit_msg], opts.repo_root, check=False)
    if proc.returncode != 0:
        # Pre-commit hook failure → route into fix loop.
        state["iteration_count"] += 1
        _persist_state(opts, state)
        if state["iteration_count"] > opts.max_iterations:
            state["status"] = "blocked"
            state["blocker"] = (
                f"Phase {phase.label} stalled at boundary commit after "
                f"{opts.max_iterations} iterations"
            )
            _persist_state(opts, state)
            return ConductResult(
                status="blocked",
                state=state,
                summary=state["blocker"],
                diagnostic=(proc.stdout + proc.stderr)[-2000:],
            )
        # Signal the caller to re-enter the loop. We do this by returning a
        # special marker the caller checks. But simpler: raise a sentinel.
        raise _CommitHookFailure(output=proc.stdout + proc.stderr)

    new_head = _head_sha(opts.repo_root)
    completed = {
        "index": phase.position,
        "label": phase.label,
        "title": phase.title,
        "commit_sha": new_head,
        "tests": "passed",
        "iterations": state["iteration_count"],
    }
    state.setdefault("completed_phases", []).append(completed)
    return ConductResult(status="running", state=state, summary="")


class _CommitHookFailure(Exception):
    def __init__(self, output: str) -> None:
        self.output = output


def _handback(
    opts: ConductOptions,
    state: dict,
    phase: Phase,
    test_status: str,
    iteration: int,
    strategy: str,
    strategy_reason: str,
    warnings: list[str],
) -> ConductResult:
    state["status"] = "awaiting_user"
    _persist_state(opts, state)
    summary = (
        f"Phase {phase.label}: {phase.title}\n"
        f"  Spawn: {strategy} ({strategy_reason})\n"
        f"  Tests: {test_status}\n"
        f"  Iterations: {iteration}\n"
        + ("".join(f"  Warning: {w}\n" for w in warnings) if warnings else "")
    )
    next_cmd = f"Run: /conduct --resume {opts.plan_path}"
    result = ConductResult(
        status="awaiting_user",
        state=state,
        summary=summary,
        next_command=next_cmd,
    )
    if opts.on_handback:
        opts.on_handback(state)
    return result


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------


def conduct(opts: ConductOptions) -> ConductResult:
    """Run preflight + the next unfinished phase, then hand back.

    Mirrors SKILL.md Step 9: every phase boundary returns control to the user.
    Tests drive multi-phase runs by re-invoking with ``resume=True``.
    """
    pre = run_preflight(opts)
    if pre is not None:
        return pre

    sp = _state_path(opts)
    sp.parent.mkdir(parents=True, exist_ok=True)
    lock = StateLock(str(sp.with_suffix(sp.suffix + ".lock")))
    with lock:
        state = _load_or_init_state(opts)

        plan_text = opts.plan_path.read_text()
        phases = [p for p in parse_phases(plan_text) if not p.is_complete]
        # phase_index in state is the count of completed phases.
        idx = len(state.get("completed_phases", []))
        if idx >= len(phases):
            state["status"] = "complete"
            _persist_state(opts, state)
            return ConductResult(status="complete", state=state, summary="All phases complete")

        phase = phases[idx]
        try:
            return _run_phase(opts, state, phase)
        except _CommitHookFailure as hook_fail:
            # Re-enter the loop with hook output as the failure context. Easiest
            # way is recursion with the failure carried via state — but state
            # already holds iteration_count; we pass the failure text through
            # by routing back into _run_phase with prior_diff / test_failures
            # set on the next request. To keep the implementation simple we
            # adopt an explicit retry here.
            return _retry_after_hook_failure(opts, state, phase, hook_fail.output)


def _retry_after_hook_failure(
    opts: ConductOptions,
    state: dict,
    phase: Phase,
    hook_output: str,
) -> ConductResult:
    """Respawn implementer with hook output as test_failures, then re-enter.

    SKILL.md Step 8.3: pre-commit hook failure routes back into Step 6 as a
    fix-loop iteration. iteration_count was already incremented before raising.
    """
    base_sha = _phase_baseline(state)
    iteration = state["iteration_count"]
    prior_diff = _staged_diff(opts.repo_root)
    _reset_index(opts.repo_root)

    while True:
        req = SpawnRequest(
            role="implementer",
            plan_path=str(opts.plan_path),
            phase_position=phase.position,
            phase_label=phase.label,
            phase_title=phase.title,
            iteration=iteration,
            base_sha=base_sha,
            prior_diff=prior_diff,
            test_failures=hook_output,
        )
        text = opts.spawn(req)
        try:
            parse_report(text, "implementer")
        except SchemaError as exc:
            state["status"] = "schema_error"
            state["blocker"] = str(exc)
            _persist_state(opts, state)
            return ConductResult(status="schema_error", state=state, summary=str(exc))

        # Tests
        test_cmd = _resolve_test_cmd(opts, phase)
        if test_cmd is not None:
            result = opts.test_runner(test_cmd, opts.test_timeout)
            if result.returncode != 0 or result.timed_out:
                state["iteration_count"] += 1
                _persist_state(opts, state)
                if state["iteration_count"] > opts.max_iterations:
                    state["status"] = "blocked"
                    state["blocker"] = (
                        f"Phase {phase.label} stalled after {opts.max_iterations} iterations"
                    )
                    _persist_state(opts, state)
                    return ConductResult(status="blocked", state=state, summary=state["blocker"])
                prior_diff = _staged_diff(opts.repo_root)
                _reset_index(opts.repo_root)
                hook_output = result.output
                iteration = state["iteration_count"]
                continue

        warnings: list[str] = []
        try:
            commit_outcome = _commit_phase(opts, state, phase, base_sha, warnings)
        except _CommitHookFailure as exc:
            prior_diff = _staged_diff(opts.repo_root)
            _reset_index(opts.repo_root)
            hook_output = exc.output
            iteration = state["iteration_count"]
            continue
        if commit_outcome.status != "running":
            return commit_outcome
        return _handback(
            opts, state, phase, "passed", iteration, "sequential", "post-hook-fix", warnings
        )


# ---------------------------------------------------------------------------
# Pause / abort helpers
# ---------------------------------------------------------------------------


def pause_phase(opts: ConductOptions) -> ConductResult:
    """`--pause-phase`: stash work, mark state paused, exit."""
    sp = _state_path(opts)
    if not sp.exists():
        return ConductResult(status="awaiting_user", state={}, summary="no active run")
    state = json.loads(sp.read_text())
    label = state.get("current_phase_title", "?")
    msg = f"conduct-pause-phase-{label}"
    _git(["stash", "push", "-u", "-m", msg], opts.repo_root, check=False)
    state["status"] = "paused"
    _persist_state(opts, state)
    return ConductResult(status="paused", state=state, summary=f"paused: {msg}")


def abort_run(opts: ConductOptions) -> ConductResult:
    """`--abort-run`: delete state. No git ops, no stash."""
    sp = _state_path(opts)
    if sp.exists():
        sp.unlink()
    return ConductResult(status="aborted", state={}, summary="state deleted")
