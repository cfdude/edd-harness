"""Default judge backend: the local `claude` CLI pinned to Haiku (subscription/flat-cost)."""

from __future__ import annotations

import shutil
import subprocess

from ..errors import EddJudgeUnavailable
from .base import JsonVerdictBackend, build_grading_prompt


class ClaudeCliJudge(JsonVerdictBackend):
    name = "claude-cli"

    def __init__(self, model: str = "haiku", timeout: float = 60.0) -> None:
        self.model = model
        self.timeout = timeout

    @staticmethod
    def available() -> bool:
        return shutil.which("claude") is not None

    def _invoke(self, rendered: str, criteria: str) -> str:
        if not self.available():
            raise EddJudgeUnavailable(
                "claude CLI not found on PATH; install it or use the Ollama backend"
            )
        prompt = build_grading_prompt(rendered, criteria)
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--model", self.model],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EddJudgeUnavailable(f"claude CLI invocation failed: {exc}") from exc
        if proc.returncode != 0:
            raise EddJudgeUnavailable(
                f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[:200]}"
            )
        return proc.stdout
