# llm-eval-harness

![CI](https://github.com/chandrapaldeora0803-creator/llm-eval-harness/actions/workflows/ci.yml/badge.svg)

A small, dependency-light harness for evaluating large language models on **coding, reasoning and structured-extraction** tasks. It runs a task suite against any OpenAI-compatible API, scores every response automatically, **classifies each failure by root cause**, and writes a Markdown report with a one-line reproduction command per failure.

## Why

A single accuracy number hides *why* a model fails. This harness separates broken code from wrong reasoning from instruction-following problems, so every failure can be turned into an actionable bug report for whoever owns the model or the prompt.

## Features

- Works with any `/chat/completions` endpoint (OpenAI, Groq, Together, vLLM, local Ollama)
- Four scorers: `exact`, `final_answer`, `json_fields`, and `python_tests` (executes generated code against unit tests in a subprocess with a timeout)
- Failure taxonomy: `syntax`, `runtime`, `assertion`, `timeout`, `format`, `wrong_answer`, `refusal`, `empty`, `api_error`, `harness_error`
- Concurrent execution, retries with exponential backoff on 429/5xx
- Markdown + JSON reports with a repro command for each failure
- `--mock` mode (no API key) and a `--min-pass-rate` gate for CI

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. No API key needed - uses canned answers from the task file
python -m evalharness --mock

# 2. Any OpenAI-compatible API
export EVAL_API_KEY=your_key
python -m evalharness --model <model-name>

# 3. Local model via Ollama
python -m evalharness --model llama3 --base-url http://localhost:11434/v1

# Re-run a single failing task
python -m evalharness --model <model-name> --only code-002
```

Example output of the mock run:

```text
3/7 passed (43%) -> reports/report.md
  assertion      1
  syntax         1
  wrong_answer   1
  format         1
```

## How it works

```text
tasks.jsonl -> Provider (API / mock) -> Scorer -> Classifier -> Report (Markdown + JSON)
```

| Module | Responsibility |
|---|---|
| `models.py` | Dataclasses: `Task`, `ModelResponse`, `ScoreResult`, `EvalRecord` |
| `providers.py` | OpenAI-compatible HTTP client with retries/backoff, plus `MockProvider` |
| `scorers.py` | Pluggable scorers; code is compiled first, then executed against tests with a timeout |
| `classifier.py` | Maps a scored response to exactly one failure type |
| `runner.py` | Loads tasks, runs them concurrently, isolates per-task errors |
| `report.py` | Aggregates results by category and failure type, renders the report |
| `cli.py` | Command-line interface |

## Writing tasks

One JSON object per line in `tasks/*.jsonl`:

```json
{"id": "reason-001", "category": "reasoning", "system": "Give the final answer as 'ANSWER: <value>'.", "prompt": "...", "scorer": "final_answer", "expected": "12:15"}
```

| Scorer | Passes when |
|---|---|
| `exact` | Normalised response equals `expected` |
| `final_answer` | The last `ANSWER:` line equals `expected` (missing line = `format` failure) |
| `json_fields` | Response is a JSON object containing every field in `expected` with matching values |
| `python_tests` | Extracted code compiles and the `tests` assertions pass within the timeout |

## Design decisions

- **Classify, don't just count.** Each failure gets exactly one type, so the report shows *where* to look (prompt, reasoning or code generation).
- **Compile before executing.** Syntax errors are caught with `compile()` without running anything, which keeps the `syntax` and `runtime` categories separate.
- **Trust the last answer.** Models often self-correct mid-response, so `final_answer` uses the last `ANSWER:` line.
- **One bad task never kills a run.** Scorer exceptions are recorded as `harness_error` instead of crashing.
- **Temperature 0** for reproducibility.

## Security note

`python_tests` executes model-generated code in a subprocess with a timeout, but **not** in a sandbox. Only run it on trusted task suites, or inside a container / disposable VM.

## Tests

```bash
python -m pytest -v
```

## Roadmap

- Numeric tolerance and unit-aware answer matching
- Docker sandbox for code execution
- Side-by-side comparison of two models on the same suite
- Tool-call / function-calling evaluation tasks
- LLM-as-judge scorer for open-ended answers
