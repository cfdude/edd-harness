import pytest

from edd_harness.errors import EddJudgeUnavailable
from edd_harness.judge.base import JsonVerdictBackend, JudgeBackend, Verdict, parse_verdict
from edd_harness.judge.fake import FakeJudge


def test_parse_verdict_plain_json():
    v = parse_verdict('{"verified": true, "reason": "ok"}')
    assert v == Verdict(True, "ok")


def test_parse_verdict_embedded_in_prose():
    v = parse_verdict('Sure!\n{"verified": false, "reason": "no downside cited"}\nThanks')
    assert v.verified is False
    assert "downside" in v.reason


def test_parse_verdict_unparseable_raises_valueerror():
    with pytest.raises(ValueError):
        parse_verdict("not json at all")


class _FlakyBackend(JsonVerdictBackend):
    name = "flaky"
    model = "flaky-1"

    def __init__(self, outputs):
        self._outputs = list(outputs)

    def _invoke(self, rendered, criteria):
        return self._outputs.pop(0)


def test_retry_once_then_parse_succeeds():
    b = _FlakyBackend(["garbage", '{"verified": true}'])
    assert b.verify("r", "c").verified is True


def test_unparseable_after_retry_raises_unavailable_not_false():
    b = _FlakyBackend(["garbage", "still garbage"])
    with pytest.raises(EddJudgeUnavailable):
        b.verify("r", "c")


def test_fake_judge_is_a_backend_and_records_calls():
    fj = FakeJudge(verified=True, reason="ok")
    assert isinstance(fj, JudgeBackend)
    assert fj.verify("rendered", "criteria") == Verdict(True, "ok")
    assert fj.calls == [("rendered", "criteria")]


def test_fake_judge_unavailable():
    with pytest.raises(EddJudgeUnavailable):
        FakeJudge(unavailable=True).verify("r", "c")
