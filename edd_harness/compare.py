"""Before/after comparison: join a run to the blessed baseline per (scenario, scorer) under
the matching {model, judge} axis key and classify each check. Any REGRESSED -> the gate fails.
INDETERMINATE is never a regression. A run whose axis has no baseline classifies all NEW.
"""

from __future__ import annotations

from dataclasses import dataclass

from .runner import FAIL, INDETERMINATE, PASS, RunResult
from .store import _load_baseline, axis_key

NEW = "NEW"
REGRESSED = "REGRESSED"
FIXED = "FIXED"
STABLE = "STABLE"
INDETERMINATE_CLS = "INDETERMINATE"


@dataclass
class CheckComparison:
    scenario_id: str
    scorer_name: str
    baseline_status: str | None
    current_status: str
    classification: str


@dataclass
class Comparison:
    items: list[CheckComparison]
    has_regression: bool


def _classify(baseline_status: str | None, current_status: str) -> str:
    if baseline_status is None:
        return NEW
    if current_status == INDETERMINATE:
        return INDETERMINATE_CLS
    if baseline_status == PASS and current_status == FAIL:
        return REGRESSED
    if baseline_status == FAIL and current_status == PASS:
        return FIXED
    return STABLE


def compare(run: RunResult, baseline: dict) -> Comparison:
    ak = axis_key(run.model_under_test, run.judge_model)
    axis = baseline.get("axes", {}).get(ak)
    baseline_checks = axis["checks"] if axis else None

    items: list[CheckComparison] = []
    for sr in run.scenarios:
        for c in sr.checks:
            key = f"{sr.scenario_id}::{c.name}"
            if baseline_checks is None or key not in baseline_checks:
                base_status = None
            else:
                base_status = baseline_checks[key]["status"]
            items.append(
                CheckComparison(
                    scenario_id=sr.scenario_id,
                    scorer_name=c.name,
                    baseline_status=base_status,
                    current_status=c.status,
                    classification=_classify(base_status, c.status),
                )
            )
    has_regression = any(i.classification == REGRESSED for i in items)
    return Comparison(items=items, has_regression=has_regression)


def compare_run(run: RunResult, root: str = ".") -> Comparison:
    """Convenience: load the baseline from ``root/.edd`` and compare."""
    return compare(run, _load_baseline(root))
