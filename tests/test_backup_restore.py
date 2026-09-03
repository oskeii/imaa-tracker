import sqlite3

import pytest

from imaa_tracker.core import db


def _insert_session(date="2026-01-01", title="Test Title", medium="anime"):
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO immersion_sessions "
            "(date, title_text, medium_type, activity_type, duration_minutes) "
            "VALUES (?, ?, ?, 'reading', 30)",
            (date, title, medium),
        )
        return cur.lastrowid


def _session_count():
    with db.connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM immersion_sessions").fetchone()[0]


class TestRestore:

    def test_restore_reverts_rows_added_after_backup(self, test_db, tmp_path):
        _insert_session(title="Before Backup")
        backup = db.backup_database(str(tmp_path / "b.db"))

        _insert_session(title="After Backup")
        assert _session_count() == 2

        db.restore_database(backup)
        assert _session_count() == 1
        with db.connect() as conn:
            titles = [r[0] for r in conn.execute(
                "SELECT title_text FROM immersion_sessions")]
            assert titles == ["Before Backup"]

    def test_restore_recovers_deleted_rows(self, test_db, tmp_path):
        sid = _insert_session(title="My Precious")
        _insert_session()
        backup = db.backup_database(str(tmp_path / "b.db"))

        with db.connect() as conn:
            conn.execute("DELETE FROM immersion_sessions WHERE id = ?", (sid,))
        assert _session_count() == 1

        db.restore_database(backup)
        assert _session_count() == 2
        with db.connect() as conn:
            titles = [r[0] for r in conn.execute(
                "SELECT title_text FROM immersion_sessions")]
            assert titles == ["My Precious", "Test Title"]

    def test_only_restores_data_from_time_of_backup(self, test_db, tmp_path):
        _insert_session(title="Original")
        backup = db.backup_database(str(tmp_path / "b.db"))
        _insert_session(title="Too Late")

        db.restore_database(backup)

        with db.connect() as conn:   # brand-new connection, re-reads WAL state
            rows = conn.execute(
                "SELECT title_text FROM immersion_sessions").fetchall()
        assert [r[0] for r in rows] == ["Original"]

    def test_restore_leaves_database_consistent(self, test_db, tmp_path):
        _insert_session()
        backup = db.backup_database(str(tmp_path / "b.db"))
        db.restore_database(backup)

        with db.connect() as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    def test_restore_preserves_schema_version(self, test_db, tmp_path):
        backup = db.backup_database(str(tmp_path / "b.db"))
        db.restore_database(backup)
        assert db.get_schema_version() == db.SCHEMA_VERSION


class TestInspectBackup:

    def test_reports_metadata(self, test_db, tmp_path):
        _insert_session()
        _insert_session(date="2026-01-02")
        backup = db.backup_database(str(tmp_path / "b.db"))

        info = db.inspect_backup(backup)
        assert info["session_count"] == 2
        assert info["schema_version"] == db.SCHEMA_VERSION
        assert info["size_bytes"] > 0

    def test_rejects_missing_file(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            db.inspect_backup(tmp_path / "no.db")

    def test_rejects_non_sqlite_file(self, tmp_path):
        junk = tmp_path / "cover.jpg"
        junk.write_bytes(b"\xff\xd8\xff\xe0 not a database at all")
        with pytest.raises(ValueError, match="not a database"):
            db.inspect_backup(junk)

    def test_rejects_unrelated_database(self, tmp_path):
        other = tmp_path / "other.db"
        with sqlite3.connect(other) as conn:
            conn.execute("CREATE TABLE recipes (id INTEGER PRIMARY KEY)")
        with pytest.raises(ValueError, match="Not an imaa-tracker database"):
            db.inspect_backup(other)

    def test_rejects_future_schema_version(self, test_db, tmp_path):
        backup = db.backup_database(str(tmp_path / "b.db"))
        with sqlite3.connect(backup) as conn:
            conn.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 10}")
        with pytest.raises(ValueError, match="Update the app"):
            db.inspect_backup(backup)

    def test_inspect_does_not_create_a_file(self, tmp_path):
        """mode=ro should not be able to create a non-existing database"""
        ghost = tmp_path / "ghost.db"
        with pytest.raises(ValueError):
            db.inspect_backup(ghost)
        assert not ghost.exists()

