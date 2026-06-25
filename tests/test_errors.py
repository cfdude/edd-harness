from edd_harness.errors import EddContractError, EddJudgeUnavailable


def test_error_types_are_exceptions():
    assert issubclass(EddContractError, Exception)
    assert issubclass(EddJudgeUnavailable, Exception)


def test_errors_can_be_raised_and_caught():
    for exc in (EddContractError, EddJudgeUnavailable):
        try:
            raise exc("boom")
        except exc as e:
            assert "boom" in str(e)
