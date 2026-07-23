from pathlib import Path

from aje.config import Settings


def test_database_url_defaults_from_data_dir(tmp_path: Path):
    s = Settings(data_dir=tmp_path, _env_file=None)
    assert s.database_url == f"sqlite:///{(tmp_path / 'aje.sqlite3').as_posix()}"


def test_env_overrides_api_key(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AJE_ANTHROPIC_API_KEY", "sk-test")
    s = Settings(data_dir=tmp_path, _env_file=None)
    assert s.anthropic_api_key == "sk-test"
