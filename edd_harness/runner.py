"""The runner: invoke adapter (x samples) -> score every scorer independently ->
per-scorer fold -> three-valued scenario verdict.

INDETERMINATE arises from exceptions (adapter raise, non-JSON output, scorer raise, judge
unavailable/unparseable) and is excluded from pass/fail accounting. Judge backends are resolved
ONCE per run and injected into judge scorers — consumers never supply a backend.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .adapter import invoke_adapter
from .judge.base import JudgeBackend
from .judge.factory import resolve_backend
from .scenario import Scenario, Suite

PASS = "pass"
FAIL = "fail"
INDETERMINATE = "indeterminate"


@dataclass
class CheckResult:
    name: str
    kind: str  # "deterministic" | "judge"
    status: str  # PASS | FAIL | INDETERMINATE
    reason: str = ""
    per_sample: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    scenario_id: str
    verdict: str
    checks: list[CheckResult]
    outputs: list[dict[str, Any]]
    samples: int
    tags: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    model_under_test: str
    judge_model: str | None
    scenarios: list[ScenarioResult]


def _is_judge(scorer: Any) -> bool:
    return bool(getattr(scorer, "requires_judge", False))


def _fold(kind: str, per_sample: list[str], k: int) -> str:
    """Per-scorer fold. Any INDETERMINATE sample => INDETERMINATE (never a false fail).
    Deterministic: all N must pass. Judge: at least k of N verified."""
    if INDETERMINATE in per_sample:
        return INDETERMINATE
    if kind == "judge":
        verified = sum(1 for s in per_sample if s == PASS)
        return PASS if verified >= k else FAIL
    return PASS if all(s == PASS for s in per_sample) else FAIL


def _scenario_verdict(checks: list[CheckResult]) -> str:
    if any(c.status == FAIL for c in checks):
        return FAIL
    if any(c.status == INDETERMINATE for c in checks):
        return INDETERMINATE
    return PASS


def run(
    suite: Suite | Iterable[Scenario],
    *,
    model_under_test: str,
    judge_backend: JudgeBackend | None = None,
    no_judge: bool = False,
    tags: Iterable[str] = (),
) -> RunResult:
    if not model_under_test:
        raise ValueError("model_under_test is required")
    if not isinstance(suite, Suite):
        suite = Suite(suite)
    if tags:
        suite = suite.filter_tags(tags)

    needs_judge = (not no_judge) and any(
        _is_judge(sc) for scenario in suite for sc in scenario.scorers
    )
    backend: JudgeBackend | None = None
    judge_model: str | None = None
    if needs_judge:
        backend = judge_backend or resolve_backend(model_under_test=model_under_test)
        if backend.model == model_under_test:
            raise ValueError(
                f"judge_model ({backend.model!r}) must differ from model_under_test"
            )
        judge_model = backend.model

    results: list[ScenarioResult] = []
    for scenario in suite:
        scorers = [sc for sc in scenario.scorers if not (no_judge and _is_judge(sc))]
        for sc in scorers:
            if _is_judge(sc):
                sc.bind(backend, judge_model)

        n = max(1, scenario.samples)
        outputs: list[dict[str, Any]] = []
        names = [sc.name for sc in scorers]
        per_sample: dict[str, list[str]] = {name: [] for name in names}
        reasons: dict[str, str] = dict.fromkeys(names, "")
        metas: dict[str, dict] = {name: {} for name in names}
        kinds = {sc.name: ("judge" if _is_judge(sc) else "deterministic") for sc in scorers}

        for _ in range(n):
            output: dict[str, Any] | None = None
            try:
                output = invoke_adapter(scenario.adapter, scenario.input).output
                outputs.append(output)
            except Exception:
                output = None
            for sc in scorers:
                if output is None:
                    per_sample[sc.name].append(INDETERMINATE)
                    continue
                try:
                    res = sc.score(output)
                    per_sample[sc.name].append(PASS if res.passed else FAIL)
                    if not res.passed and res.reason:
                        reasons[sc.name] = res.reason
                    if res.meta:
                        metas[sc.name] = res.meta
                except Exception as exc:
                    per_sample[sc.name].append(INDETERMINATE)
                    reasons[sc.name] = f"{type(exc).__name__}: {exc}"

        checks: list[CheckResult] = []
        for sc in scorers:
            kind = kinds[sc.name]
            k = sc.k if (kind == "judge" and getattr(sc, "k", None)) else math.ceil(n / 2)
            status = _fold(kind, per_sample[sc.name], k)
            checks.append(
                CheckResult(
                    name=sc.name,
                    kind=kind,
                    status=status,
                    reason="" if status == PASS else reasons[sc.name],
                    per_sample=per_sample[sc.name],
                    meta=metas[sc.name],
                )
            )

        results.append(
            ScenarioResult(
                scenario_id=scenario.id,
                verdict=_scenario_verdict(checks),
                checks=checks,
                outputs=outputs,
                samples=n,
                tags=list(scenario.tags),
            )
        )

    return RunResult(model_under_test=model_under_test, judge_model=judge_model, scenarios=results)
