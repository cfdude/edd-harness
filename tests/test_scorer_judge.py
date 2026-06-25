from dataclasses import dataclass

import pytest

from edd_harness.errors import EddJudgeUnavailable
from edd_harness.scorer import JudgeScorer


@dataclass
class _Verdict:
    verified: bool
    reason: str = ""


class FakeJudge:
    name = "fake"
    model = "fake-judge-1"

    def __init__(self, verified=True, raise_unavailable=False):
        self._verified = verified
        self._raise = raise_unavailable
        self.seen = []

    def verify(self, rendered, criteria):
        if self._raise:
            raise EddJudgeUnavailable("backend down")
        self.seen.append((rendered, criteria))
        return _Verdict(self._verified, "ok" if self._verified else "nope")


def test_unbound_judge_scorer_raises():
    js = JudgeScorer("role-c_cites", "does it cite a concrete downside?")
    with pytest.raises(RuntimeError):
        js.score({"p1": {}})


def test_judge_scorer_records_binary_and_metadata():
    js = JudgeScorer("role-c_cites", "criteria text", context_keys=("p1",)).bind(
        FakeJudge(verified=True), "fake-judge-1"
    )
    r = js.score({"p1": {"role-c": "rationale"}, "secret": "hidden"})
    assert r.passed is True
    assert r.meta["judge"] is True
    assert r.meta["backend"] == "fake"
    assert r.meta["judge_model"] == "fake-judge-1"
    assert r.meta["criteria"] == "criteria text"


def test_judge_scorer_context_keys_slice_only_selected():
    fake = FakeJudge(verified=True)
    JudgeScorer("x", "c", context_keys=("p1",)).bind(fake, "m").score(
        {"p1": {"a": 1}, "p2": {"b": 2}}
    )
    rendered = fake.seen[0][0]
    assert "p1" in rendered and "p2" not in rendered


def test_judge_unavailable_propagates():
    js = JudgeScorer("x", "c").bind(FakeJudge(raise_unavailable=True), "m")
    with pytest.raises(EddJudgeUnavailable):
        js.score({})
