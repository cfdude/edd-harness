import glob

from typer.testing import CliRunner

from edd_harness.cli import app
from edd_harness.judge.base import Verdict

runner = CliRunner()


class _SeqJudge:
    """Flat-cost-shaped fake judge that returns successive verdicts across runs."""

    name = "seq"
    model = "seq-judge-1"

    def __init__(self, verdicts):
        self._v = list(verdicts)
        self.i = 0

    def verify(self, rendered, criteria):
        v = self._v[self.i % len(self._v)]
        self.i += 1
        return Verdict(verified=v, reason="" if v else "no")


_JUDGE = (
    "from edd_harness.scenario import Scenario\n"
    "from edd_harness.scorer import check, JudgeScorer\n"
    "SCENARIOS=[Scenario(id='s1', input={}, adapter=lambda i: {'a': 5, 'txt': 'hi'},\n"
    " scorers=[check('a_ok', lambda o: o['a'] > 3),\n"
    "          JudgeScorer('polite', 'is it polite?', render=lambda o: o['txt'])])]\n"
)


def _write_judge_corpus(tmp_path, monkeypatch):
    (tmp_path / "judge_corpus.py").write_text(_JUDGE)
    monkeypatch.syspath_prepend(str(tmp_path))


_PASS = (
    "from edd_harness.scenario import Scenario\n"
    "from edd_harness.scorer import check\n"
    "SCENARIOS=[Scenario(id='s1', input={}, adapter=lambda i: {'a': 5},"
    " scorers=[check('a_gt_3', lambda o: o['a'] > 3)])]\n"
)
_FAIL = _PASS.replace("'a': 5", "'a': 1")


def _write_corpus(tmp_path, monkeypatch):
    (tmp_path / "pass_corpus.py").write_text(_PASS)
    (tmp_path / "fail_corpus.py").write_text(_FAIL)
    monkeypatch.syspath_prepend(str(tmp_path))


def _latest_run(root):
    return sorted(glob.glob(f"{root}/.edd/runs/*.jsonl"))[-1]


def test_run_no_judge_records_and_exits_zero(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch)
    res = runner.invoke(
        app,
        [
            "run",
            "pass_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--no-judge",
            "--root",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.output
    assert glob.glob(f"{tmp_path}/.edd/runs/*.jsonl")


def test_bless_then_stable_run_exits_zero(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            "run",
            "pass_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--no-judge",
            "--root",
            str(tmp_path),
        ],
    )
    b = runner.invoke(app, ["bless", _latest_run(tmp_path), "--root", str(tmp_path)])
    assert b.exit_code == 0, b.output
    res = runner.invoke(
        app,
        [
            "run",
            "pass_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--baseline",
            "--no-judge",
            "--root",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.output


def test_regression_exits_nonzero(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            "run",
            "pass_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--no-judge",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["bless", _latest_run(tmp_path), "--root", str(tmp_path)])
    res = runner.invoke(
        app,
        [
            "run",
            "fail_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--baseline",
            "--no-judge",
            "--root",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 1, res.output
    assert "REGRESSION" in res.output


def test_rescore_command(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            "run",
            "pass_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--no-judge",
            "--root",
            str(tmp_path),
        ],
    )
    res = runner.invoke(
        app, ["rescore", _latest_run(tmp_path), "pass_corpus:SCENARIOS", "--root", str(tmp_path)]
    )
    assert res.exit_code == 0, res.output
    assert "Rescored" in res.output


def _bless_then_gate(tmp_path, monkeypatch, extra_flags):
    _write_judge_corpus(tmp_path, monkeypatch)
    seq = _SeqJudge([True, False])  # judge passes during bless run, fails during gate run
    monkeypatch.setattr("edd_harness.runner.resolve_backend", lambda *a, **k: seq)
    runner.invoke(
        app, ["run", "judge_corpus:SCENARIOS", "--model", "sys@v1", "--root", str(tmp_path)]
    )
    runner.invoke(app, ["bless", _latest_run(tmp_path), "--root", str(tmp_path)])
    return runner.invoke(
        app,
        [
            "run",
            "judge_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--baseline",
            *extra_flags,
            "--root",
            str(tmp_path),
        ],
    )


def test_cli_judge_regression_is_advisory_exit_zero(tmp_path, monkeypatch):
    res = _bless_then_gate(tmp_path, monkeypatch, extra_flags=[])
    assert res.exit_code == 0, res.output  # judge regression does not block by default
    assert "ADVISORY" in res.output


def test_cli_strict_blocks_on_judge_regression(tmp_path, monkeypatch):
    res = _bless_then_gate(tmp_path, monkeypatch, extra_flags=["--strict"])
    assert res.exit_code == 1, res.output
    assert "REGRESSION" in res.output


def test_cli_strict_without_baseline_is_noop(tmp_path, monkeypatch):
    _write_corpus(tmp_path, monkeypatch)
    res = runner.invoke(
        app,
        [
            "run",
            "pass_corpus:SCENARIOS",
            "--model",
            "sys@v1",
            "--no-judge",
            "--strict",
            "--root",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.output
