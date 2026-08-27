import pytest

from app import history


@pytest.fixture(autouse=True)
def _isolated_history_db(tmp_path, monkeypatch):
    """Every test gets its own throwaway SQLite file, so running the
    suite never reads or writes the real backend/data/debug_history.db
    that a developer might be using locally -- POST /debug has a real
    side effect now (history.save_run) on every successful run."""
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "test_history.db")
    history.init_db()
    yield
