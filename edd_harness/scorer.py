"""Scorers — the uniform scoring contract.

Every scorer (deterministic or judge) implements the same ``Scorer`` Protocol and returns a
binary ``ScoreResult``. INDETERMINATE is NOT a ``ScoreResult`` value — it is a runner-level
outcome that arises when a scorer *raises* (e.g. shape drift) or a judge is unavailable.
The runner evaluates every scorer independently, so a failing check never suppresses another.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .adapter import Output


@dataclass(frozen=True)
class ScoreResult:
    passed: bool
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Scorer(Protocol):
    name: str

    def score(self, output: Output) -> ScoreResult: ...


class _Check:
    """A deterministic scorer over the output. A raising predicate is NOT caught here:
    it propagates so the runner records the check INDETERMINATE (never FAIL)."""

    requires_judge = False

    def __init__(self, name: str, fn: Callable[[Output], bool], reason: str = "") -> None:
        self.name = name
        self._fn = fn
        self._reason = reason

    def score(self, output: Output) -> ScoreResult:
        ok = bool(self._fn(output))
        return ScoreResult(passed=ok, reason="" if ok else self._reason)


def check(name: str, fn: Callable[[Output], bool], reason: str = "") -> Scorer:
    """Build a deterministic scorer from a predicate over the output."""
    return _Check(name, fn, reason)
