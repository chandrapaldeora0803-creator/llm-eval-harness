from __future__ import annotations

from typing import Optional

from .models import ModelResponse, ScoreResult

FAILURE_TYPES = {
    "api_error": "Infrastructure / API error",
    "harness_error": "Bug in the harness itself",
    "empty": "Empty response",
    "refusal": "Unexpected refusal",
    "format": "Instruction-following / output format violation",
    "syntax": "Generated code does not compile",
    "runtime": "Generated code crashes at runtime",
    "assertion": "Code runs but logic is wrong",
    "timeout": "Code too slow or loops forever",
    "wrong_answer": "Reasoning error / wrong final answer",
}

REFUSAL_HINTS = ("i can't help", "i cannot help", "i'm unable to", "i am unable to")


def classify(response: ModelResponse, result: ScoreResult) -> Optional[str]:
    """Map a scored response to a single failure type (None if it passed)."""
    if result.passed:
        return None
    if result.signal in ("api_error", "harness_error"):
        return result.signal
    if not response.text.strip():
        return "empty"
    if any(hint in response.text.lower() for hint in REFUSAL_HINTS):
        return "refusal"
    return result.signal
