from edd_harness.judge.fake import FakeJudge
from edd_harness.runner import CheckResult, RunResult, ScenarioResult
from edd_harness.scenario import Scenario
from edd_harness.scorer import JudgeScorer, check
from edd_harness.store import rescore, write_run


def _persist(tmp_path):
    stored = RunResult(
        model_under_test="system@v1",
        judge_model="fake-judge-1",
        scenarios=[
            ScenarioResult(
                "s1", "fail", [CheckResult("old", "deterministic", "fail")], [{"a": 5}], 1
            )
        ],
    )
    return write_run(stored, root=tmp_path, timestamp="20260625T000000Z")


def _exploding_adapter(_i):
    raise AssertionError("adapter MUST NOT be called during rescore")


def test_rescore_replays_outputs_without_adapter_or_backend(tmp_path):
    path = _persist(tmp_path)
    suite = [
        Scenario(
            id="s1",
            input=None,
            adapter=_exploding_adapter,
            scorers=[check("a_gt_3", lambda o: o["a"] > 3), JudgeScorer("j", "c")],
        )
    ]
    res = rescore(path, suite)  # no judge_backend -> judge skipped, zero backend calls
    names = {c.name: c.status for c in res.scenarios[0].checks}
    assert names == {"a_gt_3": "pass"}  # re-graded against stored output; judge omitted


def test_rescore_with_flatcost_backend_regrades_judge(tmp_path):
    path = _persist(tmp_path)
    suite = [
        Scenario(
            id="s1",
            input=None,
            adapter=_exploding_adapter,
            scorers=[JudgeScorer("j", "c")],
        )
    ]
    res = rescore(path, suite, judge_backend=FakeJudge(verified=True))
    assert res.scenarios[0].checks[0].status == "pass"
