"""
api/execute.py — In-process Python code execution + test-case scoring

POST /execute_python
  Body: { sourceCode, testCases: [{input: {...}, expected_output: any}] }
  Response: { status, tests_total, tests_passed, failing_tests, stdout, stderr, results }

The candidate's code is run in a sandboxed subprocess with a hard time limit.
Each test case's input dict is unpacked as keyword arguments into the function.
The function name is extracted from the source code automatically.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import Any

from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

router = APIRouter(tags=["Execute"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class TestCase(BaseModel):
    input: dict[str, Any]
    expected_output: Any


class ExecuteRequest(BaseModel):
    sourceCode: str
    testCases: list[TestCase] = []


class TestResult(BaseModel):
    index: int
    input: dict[str, Any]
    expected: Any
    actual: Any
    passed: bool
    error: str | None = None


class ExecuteResponse(BaseModel):
    status: str          # "Accepted" | "Wrong Answer" | "Runtime Error" | "Time Limit Exceeded"
    tests_total: int
    tests_passed: int
    failing_tests: list[int]
    stdout: str
    stderr: str
    results: list[TestResult]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIMEOUT_SECONDS = 10  # per entire run (all test cases)


def _extract_function_name(source: str) -> str | None:
    """Return the first top-level function name defined in source."""
    try:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                return node.name
    except SyntaxError:
        pass
    return None


def _build_runner_script(source: str, test_cases: list[TestCase], func_name: str) -> str:
    """
    Build a self-contained Python script that:
      1. Defines the candidate's function.
      2. Runs each test case and prints a JSON line per result.
    """
    cases_json = json.dumps([
        {"input": tc.input, "expected_output": tc.expected_output}
        for tc in test_cases
    ])

    runner = textwrap.dedent(f"""
import sys, json, traceback
from typing import List, Optional, Dict, Tuple, Any

# ── Candidate code ──────────────────────────────────────────────────────────
{source}

# ── Test runner ─────────────────────────────────────────────────────────────
_cases = {cases_json}
_func  = {func_name}

for _i, _tc in enumerate(_cases):
    _inp      = _tc["input"]
    _expected = _tc["expected_output"]
    try:
        _actual = _func(**_inp)
        _passed = _actual == _expected
        print(json.dumps({{"index": _i, "passed": _passed,
                           "actual": _actual, "expected": _expected,
                           "error": None}}))
    except Exception as _e:
        print(json.dumps({{"index": _i, "passed": False,
                           "actual": None, "expected": _expected,
                           "error": traceback.format_exc()}}))
""")
    return runner


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/execute_python", response_model=ExecuteResponse)
async def execute_python(req: ExecuteRequest):
    source = req.sourceCode.strip()

    # ── Basic emptiness / placeholder guard ─────────────────────────────────
    placeholder_lines = {"# write your solution here", "# your code here", "pass"}
    non_empty = [l.strip() for l in source.splitlines() if l.strip()]
    if not non_empty or all(l in placeholder_lines for l in non_empty):
        return ExecuteResponse(
            status="No Code",
            tests_total=len(req.testCases),
            tests_passed=0,
            failing_tests=list(range(len(req.testCases))),
            stdout="",
            stderr="Please write a solution before running.",
            results=[],
        )

    # ── Syntax check ─────────────────────────────────────────────────────────
    try:
        ast.parse(source)
    except SyntaxError as e:
        return ExecuteResponse(
            status="Compilation Error",
            tests_total=len(req.testCases),
            tests_passed=0,
            failing_tests=list(range(len(req.testCases))),
            stdout="",
            stderr=f"SyntaxError: {e}",
            results=[],
        )

    # ── Extract function name ────────────────────────────────────────────────
    func_name = _extract_function_name(source)
    if not func_name:
        return ExecuteResponse(
            status="Runtime Error",
            tests_total=len(req.testCases),
            tests_passed=0,
            failing_tests=list(range(len(req.testCases))),
            stdout="",
            stderr="Could not detect a function definition in your code.",
            results=[],
        )

    # ── No test cases → just syntax-run the code ────────────────────────────
    if not req.testCases:
        return ExecuteResponse(
            status="Accepted",
            tests_total=0,
            tests_passed=0,
            failing_tests=[],
            stdout="No test cases provided.",
            stderr="",
            results=[],
        )

    # ── Build & execute the runner script in a subprocess ───────────────────
    script = _build_runner_script(source, req.testCases, func_name)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(script)
        tmp_path = tmp.name

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        raw_stdout = proc.stdout
        raw_stderr = proc.stderr
        timed_out  = False
    except subprocess.TimeoutExpired:
        raw_stdout = ""
        raw_stderr = f"Execution timed out after {TIMEOUT_SECONDS}s."
        timed_out  = True
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if timed_out:
        return ExecuteResponse(
            status="Time Limit Exceeded",
            tests_total=len(req.testCases),
            tests_passed=0,
            failing_tests=list(range(len(req.testCases))),
            stdout="",
            stderr=raw_stderr,
            results=[],
        )

    # ── Parse JSON result lines ──────────────────────────────────────────────
    results: list[TestResult] = []
    parse_errors: list[str] = []

    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            results.append(TestResult(
                index    = d["index"],
                input    = req.testCases[d["index"]].input,
                expected = d["expected"],
                actual   = d["actual"],
                passed   = d["passed"],
                error    = d.get("error"),
            ))
        except Exception:
            parse_errors.append(line)

    # If we got a runtime error before any JSON (e.g. NameError at module level)
    if not results and raw_stderr:
        return ExecuteResponse(
            status="Runtime Error",
            tests_total=len(req.testCases),
            tests_passed=0,
            failing_tests=list(range(len(req.testCases))),
            stdout=raw_stdout,
            stderr=raw_stderr,
            results=[],
        )

    tests_total  = len(req.testCases)
    tests_passed = sum(1 for r in results if r.passed)
    failing      = [r.index for r in results if not r.passed]

    overall_status = (
        "Accepted"     if tests_passed == tests_total and tests_total > 0
        else "Wrong Answer" if results
        else "Runtime Error"
    )

    combined_stderr = raw_stderr
    if parse_errors:
        combined_stderr = (combined_stderr + "\n" + "\n".join(parse_errors)).strip()

    return ExecuteResponse(
        status       = overall_status,
        tests_total  = tests_total,
        tests_passed = tests_passed,
        failing_tests= failing,
        stdout       = raw_stdout,
        stderr       = combined_stderr,
        results      = results,
    )
