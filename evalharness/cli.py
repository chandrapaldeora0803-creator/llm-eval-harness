from __future__ import annotations

import argparse
import os
import sys

from .providers import MockProvider, OpenAICompatibleProvider
from .report import write_reports
from .runner import load_tasks, run


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="evalharness",
                                description="Evaluate an LLM on a task suite and report failures.")
    p.add_argument("--tasks", default="tasks/sample_tasks.jsonl")
    p.add_argument("--model", default=os.getenv("EVAL_MODEL"))
    p.add_argument("--base-url", help="OpenAI-compatible base URL (default: $EVAL_BASE_URL)")
    p.add_argument("--mock", action="store_true", help="use canned answers, no API key needed")
    p.add_argument("--only", nargs="*", help="run only these task ids")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", default="reports")
    p.add_argument("--min-pass-rate", type=float, default=0.0,
                   help="exit with code 1 if pass rate falls below this (useful in CI)")
    args = p.parse_args(argv)

    if not args.mock and not args.model:
        p.error("--model (or $EVAL_MODEL) is required unless --mock is used")

    tasks = load_tasks(args.tasks)
    if args.only:
        wanted = set(args.only)
        tasks = [t for t in tasks if t.id in wanted]
    if not tasks:
        print("No tasks selected.", file=sys.stderr)
        return 2

    provider = MockProvider() if args.mock else OpenAICompatibleProvider(args.model, base_url=args.base_url)
    records = run(provider, tasks, workers=args.workers)
    summary = write_reports(records, args.out)

    print(f"{summary['passed']}/{summary['total']} passed ({summary['pass_rate']:.0%}) "
          f"-> {args.out}/report.md")
    for ftype, count in summary["failures"].items():
        print(f"  {ftype:<14} {count}")
    return 0 if summary["pass_rate"] >= args.min_pass_rate else 1
