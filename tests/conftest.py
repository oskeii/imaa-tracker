import pytest

from imaa_tracker.core import db


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """
    Safety net to ensure tests don't touch user database.
    Auto-use and does not initialize DB, for tests that don't need it.
    """
    monkeypatch.setattr(db, "DB_NAME", str(tmp_path))


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a fresh database for each test. Overrides _isolate_db patch"""
    test_db_path = tmp_path / "test.db"
    # monkeypatch DB_NAME for repo's db.get_connection() calls
    monkeypatch.setattr(db, "DB_NAME", str(test_db_path))
    db.init_db(str(test_db_path))
    yield str(test_db_path)

