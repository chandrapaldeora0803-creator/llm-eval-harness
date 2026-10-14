from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Task:
    id: str
    category: str  # coding | reasoning | extraction
    prompt: str
    scorer: str  # exact | final_answer | json_fields | python_tests
    expected: Any = None
    tests: Optional[str] = None
    system: Optional[str] = None
    mock_answer: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ModelResponse:
    text: str
    latency_ms: float
    error: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class ScoreResult:
    passed: bool
    signal: str = "ok"  # machine-readable reason, used by the classifier
    detail: str = ""


@dataclass
class EvalRecord:
    task_id: str
    category: str
    model: str
    passed: bool
    failure_type: Optional[str]
    detail: str
    latency_ms: float
    prompt: str
    response: str
