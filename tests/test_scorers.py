from evalharness.models import Task
from evalharness.scorers import extract_code, score, score_python_tests


def make(**kw) -> Task:
    base = {"id": "t", "category": "c", "prompt": "p", "scorer": "exact"}
    base.update(kw)
    return Task(**base)


def test_extract_code_prefers_fenced_block():
    assert extract_code("Here:\n```python\nx = 1\n```\nDone.").strip() == "x = 1"


def test_final_answer_uses_last_answer_line():
    task = make(scorer="final_answer", expected="12:15")
    assert score("ANSWER: 11:00\nwait, let me fix that\nANSWER: 12:15", task).passed


def test_missing_answer_line_is_format_failure():
    result = score("12:15", make(scorer="final_answer", expected="12:15"))
    assert not result.passed and result.signal == "format"


def test_python_tests_pass_and_assertion_failure():
    task = make(scorer="python_tests", tests="assert add(2, 3) == 5")
    assert score("```python\ndef add(a, b):\n    return a + b\n```", task).passed
    bad = score("```python\ndef add(a, b):\n    return a - b\n```", task)
    assert not bad.passed and bad.signal == "assertion"


def test_python_syntax_error_detected():
    result = score("def add(a, b)\n    return a + b", make(scorer="python_tests", tests=""))
    assert result.signal == "syntax"


def test_python_timeout_detected():
    task = make(scorer="python_tests", tests="")
    result = score_python_tests("while True:\n    pass", task, timeout=1)
    assert result.signal == "timeout"


def test_json_fields():
    task = make(scorer="json_fields", expected={"name": "Priya", "amount": "10"})
    assert score('{"name": "priya", "amount": 10}', task).passed
    assert score("not json", task).signal == "format"
    assert score('{"name": "Ravi", "amount": 10}', task).signal == "wrong_answer"
