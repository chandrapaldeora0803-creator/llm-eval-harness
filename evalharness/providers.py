from __future__ import annotations

import os
import time

import requests

from .models import ModelResponse, Task

RETRYABLE = {429, 500, 502, 503, 504}


class Provider:
    name = "base"

    def complete(self, task: Task) -> ModelResponse:
        raise NotImplementedError


class OpenAICompatibleProvider(Provider):
    """Works with any /chat/completions API (OpenAI, Groq, Together, Ollama, vLLM...)."""

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None,
                 timeout: int = 60, max_retries: int = 3):
        self.name = model
        self.model = model
        self.base_url = (base_url or os.getenv("EVAL_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("EVAL_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries

    def complete(self, task: Task) -> ModelResponse:
        messages = []
        if task.system:
            messages.append({"role": "system", "content": task.system})
        messages.append({"role": "user", "content": task.prompt})
        payload = {"model": self.model, "messages": messages, "temperature": 0}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        start = time.perf_counter()
        last_error = "unknown error"
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(f"{self.base_url}/chat/completions",
                                     json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code in RETRYABLE:
                    last_error = f"HTTP {resp.status_code}"
                    time.sleep(2 ** attempt)  # exponential backoff
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"].get("content") or ""
                return ModelResponse(text, (time.perf_counter() - start) * 1000, raw=data)
            except (requests.RequestException, KeyError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(2 ** attempt)
        return ModelResponse("", (time.perf_counter() - start) * 1000, error=last_error)


class MockProvider(Provider):
    """Returns each task's canned `mock_answer`, so the pipeline runs without an API key."""

    name = "mock"

    def complete(self, task: Task) -> ModelResponse:
        return ModelResponse(task.mock_answer or "", 0.0)
