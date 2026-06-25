"""Cost-rule-enforcing judge backend resolution.

Only flat-cost backends are registered/selectable. The metered ``ApiKeyJudge`` is intentionally
absent from the registry and unreachable by any name or auto-detection — it can only be
constructed explicitly by a consumer. If no flat-cost backend is available, resolution RAISES
rather than reaching for a metered path.
"""

from __future__ import annotations

import os

from ..errors import EddJudgeUnavailable
from .base import JudgeBackend
from .claude_cli import ClaudeCliJudge
from .ollama import OllamaJudge

# Flat-cost only. ApiKeyJudge is deliberately NOT here.
_REGISTRY = {
    "claude-cli": ClaudeCliJudge,
    "ollama": OllamaJudge,
}


def _enforce_distinct(backend: JudgeBackend, model_under_test: str | None) -> None:
    if model_under_test is not None and backend.model == model_under_test:
        raise ValueError(
            f"judge_model ({backend.model!r}) must differ from model_under_test "
            f"({model_under_test!r}); evaluate with a different model than the one under test"
        )


def resolve_backend(
    name: str | None = None, *, model_under_test: str | None = None
) -> JudgeBackend:
    """Resolve a flat-cost judge backend.

    ``name`` (or ``EDD_JUDGE_BACKEND``) selects a registered backend; if unset, probe Claude CLI
    then Ollama. Always enforces ``judge_model != model_under_test``.
    """
    name = name or os.environ.get("EDD_JUDGE_BACKEND")

    if name:
        if name not in _REGISTRY:
            raise ValueError(
                f"unknown or non-flat-cost judge backend {name!r}; choose from "
                f"{sorted(_REGISTRY)}. The metered api-key backend is opt-in only and must be "
                f"constructed explicitly (ApiKeyJudge(...))."
            )
        backend: JudgeBackend = _REGISTRY[name]()
    else:
        claude = ClaudeCliJudge()
        if claude.available():
            backend = claude
        else:
            ollama = OllamaJudge()
            if ollama.available():
                backend = ollama
            else:
                raise EddJudgeUnavailable(
                    "no flat-cost judge backend available (Claude CLI or Ollama). Install one, "
                    "pass a backend explicitly, or run with --no-judge."
                )

    _enforce_distinct(backend, model_under_test)
    return backend
