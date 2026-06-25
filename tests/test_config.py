from edd_harness.config import load_config


def test_load_config_reads_tool_edd(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.edd]\nsamples = 3\n\n[tool.edd.judge]\nbackend = "ollama"\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.samples == 3
    assert cfg.judge_backend == "ollama"


def test_load_config_missing_file_is_empty(tmp_path):
    cfg = load_config(tmp_path / "does-not-exist")
    assert cfg.samples is None
    assert cfg.judge_backend is None
