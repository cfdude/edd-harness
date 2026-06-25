"""Persistence: JSON-in-git run logs and the blessed baseline.

Run records (one JSON line per scenario, incl. verbatim outputs) live in
``.edd/runs/<ts>__<model>.jsonl``. The blessed baseline lives in ``.edd/baseline.json`` keyed by
``(scenario_id, scorer_name)`` under a ``{model_under_test, judge_model}`` axis key. Both are
plain JSON so ``git diff`` is the drift review. Only ``bless`` writes the baseline.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .runner import CheckResult, RunResult, ScenarioResult

BASELINE_NAME = "baseline.json"


def edd_dir(root: str | Path = ".") -> Path:
    return Path(root) / ".edd"


def axis_key(model_under_test: str, judge_model: str | None) -> str:
    return f"{model_under_test}|{judge_model or '-'}"


def _check_to_dict(c: CheckResult) -> dict[str, Any]:
    return {
        "name": c.name,
        "kind": c.kind,
        "status": c.status,
        "reason": c.reason,
        "per_sample": c.per_sample,
        "meta": c.meta,
    }


def write_run(run: RunResult, root: str | Path = ".", timestamp: str | None = None) -> Path:
    ts = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runs_dir = edd_dir(root) / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    safe_model = re.sub(r"[^A-Za-z0-9._@-]", "_", run.model_under_test)
    path = runs_dir / f"{ts}__{safe_model}.jsonl"
    with path.open("w") as f:
        for sr in run.scenarios:
            rec = {
                "scenario_id": sr.scenario_id,
                "verdict": sr.verdict,
                "model_under_test": run.model_under_test,
                "judge_model": run.judge_model,
                "samples": sr.samples,
                "tags": sr.tags,
                "outputs": sr.outputs,
                "checks": [_check_to_dict(c) for c in sr.checks],
            }
            f.write(json.dumps(rec) + "\n")
    return path


def read_run(path: str | Path) -> RunResult:
    scenarios: list[ScenarioResult] = []
    model_under_test = ""
    judge_model: str | None = None
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        model_under_test = rec["model_under_test"]
        judge_model = rec.get("judge_model")
        scenarios.append(
            ScenarioResult(
                scenario_id=rec["scenario_id"],
                verdict=rec["verdict"],
                checks=[CheckResult(**c) for c in rec["checks"]],
                outputs=rec.get("outputs", []),
                samples=rec.get("samples", 1),
                tags=rec.get("tags", []),
            )
        )
    return RunResult(
        model_under_test=model_under_test, judge_model=judge_model, scenarios=scenarios
    )


def _load_baseline(root: str | Path) -> dict[str, Any]:
    path = edd_dir(root) / BASELINE_NAME
    if path.exists():
        return json.loads(path.read_text())
    return {"axes": {}}


def bless(run: RunResult, root: str | Path = ".", label: str | None = None) -> Path:
    """Promote a run to the blessed baseline, under its {model, judge} axis key."""
    baseline = _load_baseline(root)
    ak = axis_key(run.model_under_test, run.judge_model)
    checks = {
        f"{sr.scenario_id}::{c.name}": {"status": c.status}
        for sr in run.scenarios
        for c in sr.checks
    }
    baseline["axes"][ak] = {
        "model_under_test": run.model_under_test,
        "judge_model": run.judge_model,
        "label": label,
        "checks": checks,
    }
    edd_dir(root).mkdir(parents=True, exist_ok=True)
    path = edd_dir(root) / BASELINE_NAME
    path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
    return path
