from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from .classifier import FAILURE_TYPES
from .models import EvalRecord


def summarize(records: list[EvalRecord]) -> dict:
    total = len(records)
    passed = sum(r.passed for r in records)
    by_category = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in records:
        by_category[r.category]["total"] += 1
        by_category[r.category]["passed"] += r.passed
    latencies = [r.latency_ms for r in records if r.latency_ms]
    return {
        "model": records[0].model if records else "n/a",
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "p50_latency_ms": round(statistics.median(latencies), 1) if latencies else 0.0,
        "by_category": dict(by_category),
        "failures": dict(Counter(r.failure_type for r in records if not r.passed).most_common()),
    }


def _excerpt(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else text[:limit] + "\n... [truncated]"


def render_markdown(summary: dict, records: list[EvalRecord]) -> str:
    out = [
        "# LLM Evaluation Report", "",
        f"- **Model:** {summary['model']}",
        f"- **Pass rate:** {summary['passed']}/{summary['total']} ({summary['pass_rate']:.0%})",
        f"- **Median latency:** {summary['p50_latency_ms']} ms", "",
        "## Results by category", "",
        "| Category | Passed | Total | Pass rate |", "|---|---|---|---|",
    ]
    for cat, s in sorted(summary["by_category"].items()):
        out.append(f"| {cat} | {s['passed']} | {s['total']} | {s['passed'] / s['total']:.0%} |")

    out += ["", "## Failure breakdown", "", "| Failure type | Meaning | Count |", "|---|---|---|"]
    for ftype, count in summary["failures"].items():
        out.append(f"| `{ftype}` | {FAILURE_TYPES.get(ftype, ftype)} | {count} |")

    out += ["", "## Failure details", ""]
    for r in (r for r in records if not r.passed):
        out += [
            f"### {r.task_id} - `{r.failure_type}`", "",
            f"**Detail:** {r.detail}", "",
            "**Prompt:**", "", "```text", _excerpt(r.prompt), "```", "",
            "**Model response:**", "", "```text", _excerpt(r.response) or "(empty)", "```", "",
            f"**Reproduce:** `python -m evalharness --model {r.model} --only {r.task_id}`", "",
        ]
    return "\n".join(out)


def write_reports(records: list[EvalRecord], out_dir) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = summarize(records)
    (out / "results.json").write_text(
        json.dumps({"summary": summary, "records": [asdict(r) for r in records]}, indent=2),
        encoding="utf-8")
    (out / "report.md").write_text(render_markdown(summary, records), encoding="utf-8")
    return summary
