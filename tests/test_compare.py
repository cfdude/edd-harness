from edd_harness.compare import (
    FIXED,
    INDETERMINATE_CLS,
    NEW,
    REGRESSED,
    STABLE,
    compare,
    compare_run,
)
from edd_harness.runner import CheckResult, RunResult, ScenarioResult
from edd_harness.store import bless


def _run(status, model="system@v1", judge="fake-1", name="det"):
    return RunResult(
        model_under_test=model,
        judge_model=judge,
        scenarios=[
            ScenarioResult("s1", status, [CheckResult(name, "deterministic", status)], [{}], 1)
        ],
    )


def test_no_baseline_all_new_no_regression():
    cmp = compare(_run("pass"), {"axes": {}})
    assert cmp.items[0].classification == NEW
    assert cmp.has_regression is False


def test_regression_detected():
    base = {"axes": {"system@v1|fake-1": {"checks": {"s1::det": {"status": "pass"}}}}}
    cmp = compare(_run("fail"), base)
    assert cmp.items[0].classification == REGRESSED
    assert cmp.has_regression is True


def test_fixed_and_stable():
    base = {"axes": {"system@v1|fake-1": {"checks": {"s1::det": {"status": "fail"}}}}}
    assert compare(_run("pass"), base).items[0].classification == FIXED
    base2 = {"axes": {"system@v1|fake-1": {"checks": {"s1::det": {"status": "pass"}}}}}
    assert compare(_run("pass"), base2).items[0].classification == STABLE


def test_indeterminate_is_never_regression():
    base = {"axes": {"system@v1|fake-1": {"checks": {"s1::det": {"status": "pass"}}}}}
    cmp = compare(_run("indeterminate"), base)
    assert cmp.items[0].classification == INDETERMINATE_CLS
    assert cmp.has_regression is False


def test_axis_mismatch_is_all_new_no_gate(tmp_path):
    # bless under model v1, then run under v2 (a model swap) -> NEW, no regression
    bless(_run("pass", model="system@v1"), root=tmp_path)
    cmp = compare_run(_run("fail", model="system@v2"), root=str(tmp_path))
    assert cmp.items[0].classification == NEW
    assert cmp.has_regression is False


def _run_kind(name, kind, status, model="system@v1", judge="fake-1"):
    return RunResult(
        model_under_test=model,
        judge_model=judge,
        scenarios=[ScenarioResult("s1", status, [CheckResult(name, kind, status)], [{}], 1)],
    )


def test_check_comparison_carries_kind():
    cmp = compare(_run("pass"), {"axes": {}})
    assert cmp.items[0].kind == "deterministic"


def test_deterministic_regression_is_blocking():
    base = {"axes": {"system@v1|fake-1": {"checks": {"s1::det": {"status": "pass"}}}}}
    cmp = compare(_run_kind("det", "deterministic", "fail"), base)
    assert cmp.has_regression is True
    assert cmp.has_blocking_regression is True
    assert [i.scorer_name for i in cmp.blocking_regressions] == ["det"]
    assert cmp.advisory_regressions == []


def test_judge_regression_is_advisory_not_blocking():
    base = {"axes": {"system@v1|fake-1": {"checks": {"s1::j": {"status": "pass"}}}}}
    cmp = compare(_run_kind("j", "judge", "fail"), base)
    assert cmp.has_regression is True
    assert cmp.has_blocking_regression is False
    assert [i.scorer_name for i in cmp.advisory_regressions] == ["j"]
    assert cmp.blocking_regressions == []
