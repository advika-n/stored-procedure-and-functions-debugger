import pytest

from app import history, user_db


@pytest.fixture(autouse=True)
def _isolated_history_db(tmp_path, monkeypatch):
    """Every test gets its own throwaway SQLite file, so running the
    suite never reads or writes the real backend/data/debug_history.db
    that a developer might be using locally -- POST /debug has a real
    side effect now (history.save_run) on every successful run."""
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "test_history.db")
    history.init_db()
    yield


@pytest.fixture(autouse=True)
def _isolated_user_db(tmp_path, monkeypatch):
    """Same isolation as _isolated_history_db above, for app.user_db's
    persistent database -- POST /debug (cursor OPEN) and POST
    /sql/execute both have real on-disk side effects now, so the suite
    must never touch the real backend/data/user_data.db a developer
    might be using locally."""
    monkeypatch.setattr(user_db, "DB_PATH", tmp_path / "test_user_data.db")
    yield
