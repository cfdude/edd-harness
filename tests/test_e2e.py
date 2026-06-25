"""End-to-end vertical slice with FakeAdapter + FakeJudge: run -> persist -> bless ->
re-run -> compare detects an injected regression. No domain vocabulary."""

from edd_harness import JudgeScorer, Scenario, bless, check, compare_run, run, write_run
from edd_harness.judge.fake import FakeJudge


def _suite(answer):
    return [
        Scenario(
            id="greeting/polite",
            input={},
            adapter=lambda i, a=answer: {"answer": a},
            samples=2,
            scorers=[
                check("non_empty", lambda o: len(o["answer"]) > 0),
                JudgeScorer("is_polite", "Is it polite?", render=lambda o: o["answer"]),
            ],
        )
    ]


def test_full_slice_blesses_and_detects_regression(tmp_path):
    judge = FakeJudge(verified=True)

    good = run(_suite("hello friend"), model_under_test="sys@v1", judge_backend=judge)
    assert good.scenarios[0].verdict == "pass"
    path = write_run(good, root=tmp_path)
    assert path.exists()
    bless(good, root=tmp_path)

    # same system -> stable, no regression
    again = run(_suite("hello friend"), model_under_test="sys@v1", judge_backend=judge)
    assert compare_run(again, root=str(tmp_path)).has_regression is False

    # regressed system: empty answer fails the non_empty check
    bad = run(_suite(""), model_under_test="sys@v1", judge_backend=judge)
    cmp = compare_run(bad, root=str(tmp_path))
    assert cmp.has_regression is True
    regressed = [i for i in cmp.items if i.classification == "REGRESSED"]
    assert [i.scorer_name for i in regressed] == ["non_empty"]
