import pytest

from imaa_tracker.core import db


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Create a fresh database for each test."""
    test_db_path = tmp_path / "test.db"
    # monkeypatch DB_NAME for repo's db.get_connection() calls
    monkeypatch.setattr(db, "DB_NAME", str(test_db_path))
    db.init_db(str(test_db_path))
    yield str(test_db_path)

