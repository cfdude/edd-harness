import glob

from typer.testing import CliRunner

from edd_harness.cli import app

runner = CliRunner()

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
