import pytest

from edd_harness.scorer import Scorer, ScoreResult, check


def test_check_passes():
    s = check("ge", lambda o: o["a"] >= o["b"])
    r = s.score({"a": 2, "b": 1})
    assert isinstance(r, ScoreResult)
    assert r.passed is True


def test_check_fails_with_reason():
    s = check("ge", lambda o: o["a"] >= o["b"], reason="a must be >= b")
    r = s.score({"a": 0, "b": 1})
    assert r.passed is False
    assert r.reason == "a must be >= b"


def test_check_predicate_raise_propagates_for_runner_indeterminate():
    s = check("missing_key", lambda o: o["nope"] is True)
    with pytest.raises(KeyError):
        s.score({"a": 1})


def test_check_satisfies_scorer_protocol():
    s = check("x", lambda o: True)
    assert isinstance(s, Scorer)
    assert s.name == "x"
    assert s.requires_judge is False
