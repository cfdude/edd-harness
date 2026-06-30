import json

from edd_harness.runner import CheckResult, RunResult, ScenarioResult
from edd_harness.store import axis_key, bless, edd_dir, read_run, write_run


def _run():
    return RunResult(
        model_under_test="system@v1",
        judge_model="fake-judge-1",
        scenarios=[
            ScenarioResult(
                scenario_id="s1",
                verdict="pass",
                checks=[
                    CheckResult("det", "deterministic", "pass", per_sample=["pass"]),
                    CheckResult("jud", "judge", "fail", reason="no", per_sample=["fail"]),
                ],
                outputs=[{"a": 1}],
                samples=1,
                tags=["phase1"],
            )
        ],
    )


def test_write_run_persists_jsonl_with_verbatim_output(tmp_path):
    path = write_run(_run(), root=tmp_path, timestamp="20260625T000000Z")
    assert path.exists()
    rec = json.loads(path.read_text().splitlines()[0])
    assert rec["scenario_id"] == "s1"
    assert rec["model_under_test"] == "system@v1"
    assert rec["judge_model"] == "fake-judge-1"
    assert rec["outputs"] == [{"a": 1}]
    assert {c["name"] for c in rec["checks"]} == {"det", "jud"}


def test_read_run_roundtrip(tmp_path):
    path = write_run(_run(), root=tmp_path, timestamp="20260625T000000Z")
    rr = read_run(path)
    assert rr.model_under_test == "system@v1"
    assert rr.scenarios[0].checks[1].status == "fail"
    assert rr.scenarios[0].outputs == [{"a": 1}]


def test_bless_writes_axis_keyed_baseline(tmp_path):
    bless(_run(), root=tmp_path)
    data = json.loads((edd_dir(tmp_path) / "baseline.json").read_text())
    ak = axis_key("system@v1", "fake-judge-1")
    assert ak in data["axes"]
    checks = data["axes"][ak]["checks"]
    assert checks["s1::det"]["status"] == "pass"
    assert checks["s1::jud"]["status"] == "fail"
    # v2: kind persisted alongside status
    assert checks["s1::det"]["kind"] == "deterministic"
    assert checks["s1::jud"]["kind"] == "judge"


def test_bless_preserves_other_axes(tmp_path):
    bless(_run(), root=tmp_path)
    other = RunResult(
        model_under_test="system@v2",
        judge_model="fake-judge-1",
        scenarios=[
            ScenarioResult("s1", "pass", [CheckResult("det", "deterministic", "pass")], [{}], 1)
        ],
    )
    bless(other, root=tmp_path)
    data = json.loads((edd_dir(tmp_path) / "baseline.json").read_text())
    assert axis_key("system@v1", "fake-judge-1") in data["axes"]
    assert axis_key("system@v2", "fake-judge-1") in data["axes"]
