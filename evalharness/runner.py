from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from .classifier import classify
from .models import EvalRecord, ScoreResult, Task
from .providers import Provider
from .scorers import score


def load_tasks(path) -> list[Task]:
    tasks = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                tasks.append(Task.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(f"{path}:{lineno}: invalid task: {exc}") from exc
    return tasks


def evaluate_task(provider: Provider, task: Task) -> EvalRecord:
    response = provider.complete(task)
    if response.error:
        result = ScoreResult(False, "api_error", response.error)
    else:
        try:
            result = score(response.text, task)
        except Exception as exc:  # never let one bad task kill the whole run
            result = ScoreResult(False, "harness_error", f"{type(exc).__name__}: {exc}")
    return EvalRecord(
        task_id=task.id, category=task.category, model=provider.name,
        passed=result.passed, failure_type=classify(response, result),
        detail=result.detail, latency_ms=round(response.latency_ms, 1),
        prompt=task.prompt, response=response.text,
    )


def run(provider: Provider, tasks: list[Task], workers: int = 4) -> list[EvalRecord]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda t: evaluate_task(provider, t), tasks))
