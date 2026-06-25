"""Local Ollama judge backend (flat-cost, zero marginal cost)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..errors import EddJudgeUnavailable
from .base import JsonVerdictBackend, build_grading_prompt


class OllamaJudge(JsonVerdictBackend):
    name = "ollama"

    def __init__(self, model: str = "llama3.1", host: str | None = None, timeout: float = 60.0):
        self.model = model
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2.0) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def _invoke(self, rendered: str, criteria: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": build_grading_prompt(rendered, criteria),
                "stream": False,
                "format": "json",
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise EddJudgeUnavailable(f"Ollama request failed: {exc}") from exc
        return body.get("response", "")
