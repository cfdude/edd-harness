from edd_harness.scenario import Scenario, Suite, load_suite


def _scn(id_, *tags):
    return Scenario(id=id_, input={"n": 1}, adapter=lambda i: {}, scorers=[], tags=tuple(tags))


def test_scenario_fields_and_defaults():
    s = _scn("a")
    assert s.id == "a"
    assert s.samples == 1
    assert s.tags == ()
    assert s.metadata == {}


def test_suite_len_and_iter():
    suite = Suite([_scn("a"), _scn("b")])
    assert len(suite) == 2
    assert [s.id for s in suite] == ["a", "b"]


def test_suite_filter_tags():
    suite = Suite([_scn("a", "phase1"), _scn("b", "phase2"), _scn("c", "phase1", "phase2")])
    assert [s.id for s in suite.filter_tags(["phase1"])] == ["a", "c"]
    assert [s.id for s in suite.filter_tags([])] == ["a", "b", "c"]


def test_load_suite_from_module(tmp_path, monkeypatch):
    (tmp_path / "mycorpus.py").write_text(
        "from edd_harness.scenario import Scenario\n"
        "SCENARIOS = [Scenario(id='x', input=1, adapter=lambda i: {}, scorers=[])]\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    suite = load_suite("mycorpus:SCENARIOS")
    assert len(suite) == 1
    assert suite.scenarios[0].id == "x"
