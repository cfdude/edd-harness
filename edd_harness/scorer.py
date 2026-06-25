"""Scorers — the uniform scoring contract.

Every scorer (deterministic or judge) implements the same ``Scorer`` Protocol and returns a
binary ``ScoreResult``. INDETERMINATE is NOT a ``ScoreResult`` value — it is a runner-level
outcome that arises when a scorer *raises* (e.g. shape drift) or a judge is unavailable.
The runner evaluates every scorer independently, so a failing check never suppresses another.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .adapter import Output

if TYPE_CHECKING:
    from .judge.base import JudgeBackend


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


class JudgeScorer:
    """An LLM-judge scorer. The consumer constructs it WITHOUT a backend; the runner injects
    the resolved backend and ``judge_model`` via ``bind()`` at evaluation time. ``score`` stays
    output-only. The verdict is coerced to binary verified/not (never Likert); a backend that
    raises ``EddJudgeUnavailable`` propagates so the runner records the check INDETERMINATE.

    ``render`` or ``context_keys`` select only the output slices shown to the judge. ``k`` is an
    optional per-scorer override of the k-of-N judge sample fold (default ``ceil(N/2)``).
    """

    requires_judge = True

    def __init__(
        self,
        name: str,
        criteria: str,
        render: Callable[[Output], str] | None = None,
        context_keys: tuple[str, ...] = (),
        k: int | None = None,
    ) -> None:
        self.name = name
        self.criteria = criteria
        self._render = render
        self._context_keys = tuple(context_keys)
        self.k = k
        self._backend: JudgeBackend | None = None
        self._judge_model: str | None = None

    def bind(self, backend: JudgeBackend, judge_model: str) -> JudgeScorer:
        """Runner-only: attach the resolved backend + judge_model before scoring."""
        self._backend = backend
        self._judge_model = judge_model
        return self

    def _rendered(self, output: Output) -> str:
        if self._render is not None:
            return self._render(output)
        if self._context_keys:
            return json.dumps({k: output.get(k) for k in self._context_keys}, sort_keys=True)
        return json.dumps(output, sort_keys=True)

    def score(self, output: Output) -> ScoreResult:
        if self._backend is None:
            raise RuntimeError(
                f"JudgeScorer {self.name!r} is not bound to a backend; the runner must inject it"
            )
        verdict = self._backend.verify(self._rendered(output), self.criteria)
        return ScoreResult(
            passed=bool(verdict.verified),
            reason=verdict.reason,
            meta={
                "judge": True,
                "backend": self._backend.name,
                "judge_model": self._judge_model,
                "criteria": self.criteria,
            },
        )
