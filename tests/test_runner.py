import pytest

from edd_harness.judge.base import Verdict
from edd_harness.runner import FAIL, INDETERMINATE, PASS, run
from edd_harness.scenario import Scenario, Suite
from edd_harness.scorer import JudgeScorer, check


class SeqAdapter:
    """Returns successive outputs across samples (cycles if exhausted)."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.i = 0

    def __call__(self, _input):
        out = self._outputs[self.i % len(self._outputs)]
        self.i += 1
        return out


class SeqJudge:
    name = "seq"
    model = "seq-judge-1"

    def __init__(self, verdicts):
        self._v = list(verdicts)
        self.i = 0

    def verify(self, rendered, criteria):
        v = self._v[self.i % len(self._v)]
        self.i += 1
        return Verdict(verified=v, reason="" if v else "no")


def _run(scenarios, **kw):
    kw.setdefault("model_under_test", "system@v1")
    return run(Suite(scenarios), **kw)


def test_model_under_test_required():
    with pytest.raises(ValueError):
        run([], model_under_test="")


def test_independent_evaluation_records_every_scorer(monkeypatch):
    # a failing deterministic check must NOT suppress the judge check's record
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"a": 0, "txt": "x"},
        scorers=[
            check("always_fail", lambda o: o["a"] == 1, reason="nope"),
            JudgeScorer("judge_ok", "c"),
        ],
    )
    r = _run([scn], judge_backend=SeqJudge([True]))
    names = {c.name: c.status for c in r.scenarios[0].checks}
    assert names["always_fail"] == FAIL
    assert names["judge_ok"] == PASS  # recorded despite the det failure


def test_deterministic_fold_requires_all_samples():
    adapter = SeqAdapter([{"a": 1}, {"a": 0}, {"a": 1}])  # one sample fails
    scn = Scenario(
        id="s",
        input={},
        adapter=adapter,
        samples=3,
        scorers=[check("a_is_1", lambda o: o["a"] == 1)],
    )
    r = _run([scn])
    assert r.scenarios[0].checks[0].status == FAIL


def test_judge_fold_k_of_n_majority_passes():
    scn = Scenario(
        id="s", input={}, adapter=lambda i: {"t": "x"}, samples=3, scorers=[JudgeScorer("j", "c")]
    )
    # 2 of 3 verified -> default k = ceil(3/2) = 2 -> pass
    r = _run([scn], judge_backend=SeqJudge([True, False, True]))
    assert r.scenarios[0].checks[0].status == PASS


def test_judge_fold_below_k_fails():
    scn = Scenario(
        id="s", input={}, adapter=lambda i: {"t": "x"}, samples=3, scorers=[JudgeScorer("j", "c")]
    )
    r = _run([scn], judge_backend=SeqJudge([True, False, False]))  # 1/3 < 2
    assert r.scenarios[0].checks[0].status == FAIL


def test_per_scorer_configurable_k():
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"t": "x"},
        samples=3,
        scorers=[JudgeScorer("j", "c", k=3)],
    )  # require all 3
    r = _run([scn], judge_backend=SeqJudge([True, True, False]))  # 2/3 < 3
    assert r.scenarios[0].checks[0].status == FAIL


def test_scorer_raise_is_indeterminate_not_fail():
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"a": 1},
        scorers=[check("bad_key", lambda o: o["missing"] == 1)],
    )
    r = _run([scn])
    assert r.scenarios[0].checks[0].status == INDETERMINATE
    assert r.scenarios[0].verdict == INDETERMINATE


def test_adapter_raise_is_indeterminate():
    def boom(i):
        raise RuntimeError("down")

    scn = Scenario(id="s", input={}, adapter=boom, scorers=[check("x", lambda o: True)])
    r = _run([scn])
    assert r.scenarios[0].checks[0].status == INDETERMINATE
    assert r.scenarios[0].verdict == INDETERMINATE


def test_non_json_output_is_indeterminate():
    scn = Scenario(
        id="s", input={}, adapter=lambda i: {"o": object()}, scorers=[check("x", lambda o: True)]
    )
    r = _run([scn])
    assert r.scenarios[0].verdict == INDETERMINATE


def test_verdict_precedence_fail_over_indeterminate():
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"a": 0},
        scorers=[check("fails", lambda o: o["a"] == 1), check("raises", lambda o: o["missing"])],
    )
    r = _run([scn])
    assert r.scenarios[0].verdict == FAIL  # fail beats indeterminate


def test_no_judge_skips_judge_scorers():
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"a": 1},
        scorers=[check("a", lambda o: o["a"] == 1), JudgeScorer("j", "c")],
    )
    r = _run([scn], no_judge=True)
    names = [c.name for c in r.scenarios[0].checks]
    assert names == ["a"]  # judge scorer omitted, no backend resolved


def test_runner_injects_backend_without_consumer_binding():
    # JudgeScorer constructed with no backend; runner binds it.
    js = JudgeScorer("j", "c")
    scn = Scenario(id="s", input={}, adapter=lambda i: {"t": "x"}, scorers=[js])
    r = _run([scn], judge_backend=SeqJudge([True]))
    assert r.scenarios[0].checks[0].status == PASS
    assert r.judge_model == "seq-judge-1"


def test_judge_must_differ_from_model_under_test():
    scn = Scenario(id="s", input={}, adapter=lambda i: {"t": "x"}, scorers=[JudgeScorer("j", "c")])
    with pytest.raises(ValueError, match="differ"):
        run(Suite([scn]), model_under_test="seq-judge-1", judge_backend=SeqJudge([True]))


def test_observed_deterministic_fail_not_masked_by_flake():
    # sample 1 fails (a != 1); sample 2 raises (missing key -> indeterminate).
    # An observed FAIL must dominate so the regression gate still catches it.
    adapter = SeqAdapter([{"a": 0}, {}])
    scn = Scenario(
        id="s",
        input={},
        adapter=adapter,
        samples=2,
        scorers=[check("a_is_1", lambda o: o["a"] == 1)],
    )
    r = _run([scn])
    assert r.scenarios[0].checks[0].status == FAIL


def test_judge_k_zero_always_passes():
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"t": "x"},
        samples=2,
        scorers=[JudgeScorer("j", "c", k=0)],
    )
    r = _run([scn], judge_backend=SeqJudge([False, False]))  # 0 verified, k=0 -> pass
    assert r.scenarios[0].checks[0].status == PASS


def test_duplicate_scorer_names_rejected():
    scn = Scenario(
        id="s",
        input={},
        adapter=lambda i: {"a": 1},
        scorers=[check("dup", lambda o: True), check("dup", lambda o: False)],
    )
    with pytest.raises(ValueError, match="duplicate scorer"):
        _run([scn])
