"""Metered, OPT-IN-ONLY judge backend (per-call ANTHROPIC_API_KEY).

This backend is deliberately NOT registered in the factory and is not selectable by any config
string or auto-detection — it is reachable only by a consumer explicitly constructing it. It
warns on construction because it incurs metered per-call cost, which the engine's default path
avoids by construction.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import warnings

from ..errors import EddJudgeUnavailable
from .base import JsonVerdictBackend, build_grading_prompt

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class ApiKeyJudge(JsonVerdictBackend):
    name = "api-key"

    def __init__(self, model: str = "claude-haiku-4-5", api_key: str | None = None, timeout=60.0):
        warnings.warn(
            "ApiKeyJudge uses a metered per-call API key and incurs cost per evaluation; "
            "the flat-cost ClaudeCliJudge/OllamaJudge backends are preferred.",
            stacklevel=2,
        )
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.timeout = timeout

    def _invoke(self, rendered: str, criteria: str) -> str:
        if not self._api_key:
            raise EddJudgeUnavailable("ApiKeyJudge requires ANTHROPIC_API_KEY")
        payload = json.dumps(
            {
                "model": self.model,
                "max_tokens": 256,
                "messages": [{"role": "user", "content": build_grading_prompt(rendered, criteria)}],
            }
        ).encode()
        req = urllib.request.Request(
            _ANTHROPIC_URL,
            data=payload,
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise EddJudgeUnavailable(f"Anthropic API request failed: {exc}") from exc
        try:
            return body["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EddJudgeUnavailable(f"unexpected Anthropic API response: {body!r}") from exc
