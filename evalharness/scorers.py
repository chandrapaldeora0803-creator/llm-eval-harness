from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

from .models import ScoreResult, Task

_CODE_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S)
_ANSWER_LINE = re.compile(r"^\s*ANSWER:\s*(.+)$", re.I | re.M)
_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)


def _norm(value) -> str:
    return " ".join(str(value).strip().lower().rstrip(".").split())


def extract_code(text: str) -> str:
    """Take the longest fenced code block; fall back to the raw text."""
    blocks = _CODE_BLOCK.findall(text)
    return max(blocks, key=len) if blocks else text


def score_exact(text: str, task: Task) -> ScoreResult:
    if _norm(text) == _norm(task.expected):
        return ScoreResult(True)
    return ScoreResult(False, "wrong_answer", f"expected {task.expected!r}, got {text.strip()[:80]!r}")


def score_final_answer(text: str, task: Task) -> ScoreResult:
    matches = _ANSWER_LINE.findall(text)
    if not matches:
        return ScoreResult(False, "format", "no 'ANSWER:' line found in response")
    got = matches[-1]  # models sometimes self-correct; trust the last one
    if _norm(got) == _norm(task.expected):
        return ScoreResult(True)
    return ScoreResult(False, "wrong_answer", f"expected {task.expected!r}, got {got.strip()!r}")


def score_json_fields(text: str, task: Task) -> ScoreResult:
    raw = _JSON_FENCE.sub("", text.strip())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ScoreResult(False, "format", f"invalid JSON: {exc}")
    if not isinstance(data, dict):
        return ScoreResult(False, "format", "expected a JSON object")
    missing = [k for k in task.expected if k not in data]
    if missing:
        return ScoreResult(False, "format", f"missing fields: {missing}")
    wrong = {k: data[k] for k, v in task.expected.items() if _norm(data[k]) != _norm(v)}
    if wrong:
        return ScoreResult(False, "wrong_answer", f"wrong values: {wrong}")
    return ScoreResult(True)


def score_python_tests(text: str, task: Task, timeout: int = 10) -> ScoreResult:
    code = extract_code(text)
    try:
        compile(code, "<model_output>", "exec")
    except SyntaxError as exc:
        return ScoreResult(False, "syntax", f"SyntaxError: {exc.msg} (line {exc.lineno})")

    program = f"{code}\n\n{task.tests or ''}\nprint('ALL_TESTS_PASSED')\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "candidate.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(program)
        try:
            proc = subprocess.run([sys.executable, path], capture_output=True,
                                  text=True, timeout=timeout, cwd=tmp)
        except subprocess.TimeoutExpired:
            return ScoreResult(False, "timeout", f"execution exceeded {timeout}s")

    if proc.returncode == 0 and "ALL_TESTS_PASSED" in proc.stdout:
        return ScoreResult(True)
    lines = proc.stderr.strip().splitlines()
    last = lines[-1] if lines else "process failed with no output"
    signal = "assertion" if last.startswith("AssertionError") else "runtime"
    return ScoreResult(False, signal, last[:300])


SCORERS = {
    "exact": score_exact,
    "final_answer": score_final_answer,
    "json_fields": score_json_fields,
    "python_tests": score_python_tests,
}


def score(text: str, task: Task) -> ScoreResult:
    try:
        scorer = SCORERS[task.scorer]
    except KeyError:
        raise ValueError(f"unknown scorer {task.scorer!r} for task {task.id}") from None
    return scorer(text, task)
