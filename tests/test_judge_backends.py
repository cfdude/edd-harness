import subprocess

import pytest

from edd_harness.errors import EddJudgeUnavailable
from edd_harness.judge.api_key import ApiKeyJudge
from edd_harness.judge.claude_cli import ClaudeCliJudge
from edd_harness.judge.factory import resolve_backend
from edd_harness.judge.ollama import OllamaJudge

# ---- concrete backends (3.3) ----


def test_claude_available_returns_bool():
    assert isinstance(ClaudeCliJudge.available(), bool)


def test_claude_invoke_missing_cli_raises_unavailable(monkeypatch):
    monkeypatch.setattr(ClaudeCliJudge, "available", staticmethod(lambda: False))
    with pytest.raises(EddJudgeUnavailable):
        ClaudeCliJudge()._invoke("r", "c")


def test_claude_invoke_nonzero_exit_raises_unavailable(monkeypatch):
    monkeypatch.setattr(ClaudeCliJudge, "available", staticmethod(lambda: True))

    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(EddJudgeUnavailable):
        ClaudeCliJudge()._invoke("r", "c")


def test_ollama_invoke_connection_failure_raises_unavailable(monkeypatch):
    def boom(*a, **k):
        raise OSError("refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(EddJudgeUnavailable):
        OllamaJudge()._invoke("r", "c")


def test_api_key_judge_warns_on_construction():
    with pytest.warns(UserWarning):
        ApiKeyJudge()


# ---- factory (3.2) + judge != MUT (3.4) ----


def test_factory_selects_named_flatcost_backend():
    assert isinstance(resolve_backend("ollama"), OllamaJudge)


def test_factory_never_returns_metered_backend():
    with pytest.raises(ValueError, match="api-key"):
        resolve_backend("api-key")


def test_factory_unknown_backend_raises():
    with pytest.raises(ValueError):
        resolve_backend("gpt-9000")


def test_factory_auto_picks_claude_when_available(monkeypatch):
    monkeypatch.delenv("EDD_JUDGE_BACKEND", raising=False)
    monkeypatch.setattr(ClaudeCliJudge, "available", staticmethod(lambda: True))
    assert isinstance(resolve_backend(), ClaudeCliJudge)


def test_factory_raises_when_no_flatcost_backend(monkeypatch):
    monkeypatch.delenv("EDD_JUDGE_BACKEND", raising=False)
    monkeypatch.setattr(ClaudeCliJudge, "available", staticmethod(lambda: False))
    monkeypatch.setattr(OllamaJudge, "available", lambda self: False)
    with pytest.raises(EddJudgeUnavailable):
        resolve_backend()


def test_factory_enforces_judge_distinct_from_model_under_test():
    with pytest.raises(ValueError, match="must differ"):
        resolve_backend("ollama", model_under_test="llama3.1")  # OllamaJudge default model
