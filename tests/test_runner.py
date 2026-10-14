from pathlib import Path

from evalharness.providers import MockProvider
from evalharness.report import write_reports
from evalharness.runner import load_tasks, run

TASKS = Path(__file__).resolve().parent.parent / "tasks" / "sample_tasks.jsonl"


def test_mock_run_classifies_every_failure(tmp_path):
    records = run(MockProvider(), load_tasks(TASKS))
    by_id = {r.task_id: r for r in records}

    assert by_id["code-001"].passed
    assert by_id["reason-001"].passed
    assert by_id["extract-001"].passed
    assert by_id["code-002"].failure_type == "assertion"
    assert by_id["code-003"].failure_type == "syntax"
    assert by_id["reason-002"].failure_type == "wrong_answer"
    assert by_id["reason-003"].failure_type == "format"

    summary = write_reports(records, tmp_path)
    assert summary["passed"] == 3 and summary["total"] == 7
    assert "code-002" in (tmp_path / "report.md").read_text(encoding="utf-8")
