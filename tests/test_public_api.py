import edd_harness

EXPECTED = [
    "Scenario",
    "Suite",
    "load_suite",
    "Scorer",
    "ScoreResult",
    "check",
    "JudgeScorer",
    "Adapter",
    "Output",
    "run",
    "RunResult",
    "ScenarioResult",
    "CheckResult",
    "write_run",
    "read_run",
    "bless",
    "rescore",
    "compare",
    "compare_run",
    "Comparison",
    "EddContractError",
    "EddJudgeUnavailable",
]


def test_public_api_is_exported():
    for name in EXPECTED:
        assert hasattr(edd_harness, name), f"missing public export: {name}"


def test_version_present():
    assert edd_harness.__version__
