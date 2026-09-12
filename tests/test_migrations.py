import os
import sqlite3
from contextlib import closing

import pytest

from imaa_tracker.core import db
from imaa_tracker.core import migrations

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _make_v0_db(path: str) -> str:
    """Build a database matching the pre-migration schema. Returns DB path"""
    with open(os.path.join(FIXTURES, "schema_v0.sql"), encoding="utf-8") as f:
        with closing(sqlite3.connect(path)) as conn:
            conn.executescript(f.read())
    return path


def _schema_fingerprint(path: str):
    """
    Structural description of the database: tables -> columns, and indexes
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    out = {}
    for t in tables:
        cols = {}
        for row in conn.execute(f"PRAGMA table_info({t})"):
            # name -> (type, notnull, default, is_pk)
            cols[row[1]] = tuple(row[i] for i in range(2, 6))
        idx = sorted(
            r[1] for r in conn.execute(f"PRAGMA index_list({t})")
            if not r[1].startswith("sqlite_autoindex")
        )
        out[t] = {"columns": cols, "indexes": idx}
    conn.close()
    return out


def test_registry_matches_schema_version():
    """All version sources must agree"""
    assert migrations.LATEST_VERSION == db.SCHEMA_VERSION


def test_fresh_matches_migrated(tmp_path):
    """A migrated (existing) database and a fresh database must be structurally identical"""
    migrated = _make_v0_db(str(tmp_path / "old.db"))
    migrations.migrate(migrated, backup=False)

    fresh = str(tmp_path / "new.db")
    db.init_db(fresh)

    fp_migrated, fp_fresh = _schema_fingerprint(migrated), _schema_fingerprint(fresh)

    assert set(fp_migrated) == set(fp_fresh), (
        f"table mismatch: only in migrated={set(fp_migrated) - set(fp_fresh)}, "
        f"only in fresh={set(fp_fresh)- set(fp_migrated)}"
    )
    for table in fp_fresh:
        assert fp_migrated[table]["columns"] == fp_fresh[table]["columns"], \
            f"column mismatch in {table}"
        assert fp_migrated[table]["indexes"] == fp_fresh[table]["indexes"], \
            f"index mismatch in {table}"

    assert db.get_schema_version(migrated) == db.get_schema_version(fresh)


def test_migrate_preserves_data(tmp_path):
    """Existing rows should survive the rebuild"""
    path = _make_v0_db(str(tmp_path / "d.db"))

    with db.connect(path) as conn:
        conn.execute(
            "INSERT INTO titles (id, name, medium_type) VALUES (1, 'キノの旅', 'light_novel')"
        )
        conn.execute(
            "INSERT INTO immersion_sessions "
            "(id, date, title_id, title_text, medium_type, activity_type, duration_minutes, character_count) "
            "VALUES (1, '2026-09-01', 1, 'キノの旅', 'light_novel', 'reading', 56, 6000)"
        )

    migrations.migrate(path, backup=False)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    t = conn.execute("SELECT * FROM titles WHERE id = 1").fetchone()
    s = conn.execute("SELECT * FROM immersion_sessions WHERE id = 1").fetchone()
    assert t["name"] == "キノの旅"
    assert s["character_count"] == 6000
    assert s["title_id"] == 1  # FK
    conn.close()


def test_migrate_is_idempotent(tmp_path):
    """Running migrations more than once is a no-op"""
    path = _make_v0_db(str(tmp_path / "d.db"))
    v1 = migrations.migrate(path, backup=False)
    v2 = migrations.migrate(path, backup=False)
    assert v1 == v2 == db.SCHEMA_VERSION


def test_check_constraints_enforced_after_migration(tmp_path):
    path = _make_v0_db(str(tmp_path / "d.db"))
    migrations.migrate(path, backup=False)

    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO titles (name, medium_type) VALUES ('ok', 'anime')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO titles (name, medium_type) VALUES ('bad', 'dog')")
    # NULL should be allowed on nullable enum column
    conn.execute("INSERT INTO titles (name, medium_type, api) VALUES ('n', 'anime', NULL)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO titles (name, medium_type, api) VALUES ('b', 'anime', 'no')")
    conn.close()


def test_migration_rejects_dirty_data_with_message(tmp_path):
    """
    A value that was allowed before (due to no constraints enforced) blocks the migrations.
    The error must say which value.
    """
    path = _make_v0_db(str(tmp_path / "d.db"))
    with db.connect(path) as conn:
        conn.execute("INSERT INTO titles (name, medium_type) VALUES ('x', 'blu_ray')")

    with pytest.raises(RuntimeError, match="blu_ray"):
        migrations.migrate(path, backup=False)

    # the failed migration must leave the database untouched after last compatible version
    assert db.get_schema_version(path) == 2  # stopped before m_003 (enforces check constraints on titles medium_type)
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM titles").fetchone()[0] == 1
    r = conn.execute("SELECT name, medium_type FROM titles").fetchone()
    assert (r[0], r[1]) == ('x', 'blu_ray')
    conn.close()


def test_refuses_future_database(tmp_path):
    """Should refuse to use a newer schema with an older version of the app."""
    path = _make_v0_db(str(tmp_path / "d.db"))
    with db.connect(path) as conn:
        conn.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 4}")

    with pytest.raises(RuntimeError, match="newer than this app"):
        migrations.migrate(path, backup=False)


def test_open_database_creates_fresh(tmp_path):
    """An empty file must be initialized, not migrated"""
    path = str(tmp_path / "new.db")
    assert migrations.open_database(path) == db.SCHEMA_VERSION
    conn = sqlite3.connect(path)
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0] > 0
    conn.close()


def test_open_database_upgrades_existing(tmp_path):
    """An empty file must be initialized, not migrated"""
    path = _make_v0_db(str(tmp_path / "old.db"))
    assert db.get_schema_version(path) == 0
    assert migrations.open_database(path) == db.SCHEMA_VERSION


def test_backup_is_written_before_migrating(tmp_path):
    path = _make_v0_db(str(tmp_path / "d.db"))
    assert len([p for p in os.listdir(tmp_path) if p.endswith(".bak")]) == 0

    migrations.migrate(path, backup=True)
    backups = [p for p in os.listdir(tmp_path) if p.endswith(".bak")]
    assert len(backups) == 1
    assert ".v0." in backups[0]  # named for the version it can restore to

    # backup must be a usable database (still at the old version)
    bak = str(tmp_path / backups[0])
    assert db.get_schema_version(bak) == 0
    conn = sqlite3.connect(bak)
    conn.execute("SELECT COUNT(*) FROM titles")  # readable
    conn.close()


def test_settings_default_seeded(tmp_path):
    path = _make_v0_db(str(tmp_path / "d.db"))
    migrations.migrate(path, backup=False)
    conn = sqlite3.connect(path)
    val = conn.execute(
        "SELECT value FROM settings WHERE key = 'active_day_minutes'"
    ).fetchone()[0]
    assert val == "15"
    conn.close()


def test_goal_enum_constraints_enforced(tmp_path):
    path = _make_v0_db(str(tmp_path / "d.db"))
    migrations.migrate(path, backup=False)
    conn = sqlite3.connect(path)

    conn.execute(
        "INSERT INTO goals (name, goal_type, metric, target_value, period) "
        "VALUES ('ok', 'recurring', 'character_count', 5000, 'daily')"
    )

    bad_inserts = [
        "INSERT INTO goals (name, goal_type, metric, target_value) "
        "VALUES ('b', 'lifetime_goal', 'character_count', 1)",
        "INSERT INTO goals (name, goal_type, metric, target_value) "
        "VALUES ('b', 'recurring', 'word_count', 1)",
        "INSERT INTO goals (name, goal_type, metric, target_value, period) "
        "VALUES ('b', 'recurring', 'character_count', 1, 'hourly')",
        "INSERT INTO goals (name, goal_type, metric, target_value, medium_type) "
        "VALUES ('b', 'recurring', 'character_count', 1, 'blu_ray')",
        "INSERT INTO goals (name, goal_type, metric, target_value, activity_type) "
        "VALUES ('b', 'recurring', 'character_count', 1, 'skimming')",
    ]
    for sql in bad_inserts:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql)

    # Nullable filters must still accept NULL.
    conn.execute(
        "INSERT INTO goals (name, goal_type, metric, target_value, medium_type) "
        "VALUES ('n', 'lifetime', 'character_count', 1000000, NULL)"
    )
    conn.close()


def test_goal_log_survives_goals_rebuild(tmp_path):
    """
    Make sure the rebuild is guarded by PRAGMA foreign_keys=OFF.
    Otherwise, goal_logs will cascade on delete when the old goals table gets dropped.
    """
    path = _make_v0_db(str(tmp_path / "d.db"))
    with db.connect(path) as conn:
        conn.execute(
            "INSERT INTO goals (id, name, goal_type, metric, target_value, period) "
            "VALUES (1, 'Daily', 'recurring', 'character_count', 5000, 'daily')"
        )
        for i in range(5):
            conn.execute(
                "INSERT INTO goal_log (goal_id, period_date, actual_value, "
                "target_value, is_achieved) VALUES (1, ?, 6000, 5000, 1)",
                (f"2026-06-0{i + 1}",),
            )

    migrations.migrate(path, backup=False)

    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM goal_log").fetchone()[0] == 5
    # goal_log wasn't rebuilt, so its indexes must be untouched.
    idx = sorted(
        r[1] for r in conn.execute("PRAGMA index_list(goal_log)")
        if not r[1].startswith("sqlite_autoindex")
    )
    assert idx == ["idx_goallog_date", "idx_goallog_goal", "idx_goallog_unique"]
    conn.close()


class TestTitleUniqueness:

    def test_duplicates_merged_and_sessions_repointed(self, tmp_path):
        """
        Two titles differing only by trailing space, merge into one,
        and sessions pointing at the dupe now point to the original
        """
        v0_db = _make_v0_db(str(tmp_path / "old.db"))
        with db.connect(v0_db) as conn:
            conn.execute("INSERT INTO titles (id, name, medium_type) VALUES (1, 'キノの旅', 'light_novel')")
            conn.execute("INSERT INTO titles (id, name, medium_type) VALUES (2, 'キノの旅 ', 'light_novel')")
            titles = conn.execute("SELECT id FROM titles WHERE name = 'キノの旅'").fetchall()
            assert len(titles) == 1
            conn.execute("INSERT INTO immersion_sessions (date, title_id, title_text, medium_type) "
                         "VALUES ('2026-01-01', 2, 'キノの旅 ', 'light_novel')")

        migrations.migrate(v0_db)

        with db.connect(v0_db) as conn:
            titles = conn.execute("SELECT id FROM titles WHERE name = 'キノの旅'").fetchall()
            assert len(titles) == 1
            assert tuple(conn.execute("SELECT title_id, title_text FROM immersion_sessions").fetchone()) == (1, "キノの旅")


class TestSessionUuid:
    def test_every_row_gets_uuid(self, tmp_path):
        v0_db = _make_v0_db(str(tmp_path / "old.db"))
        with db.connect(v0_db) as conn:
            for i in range(3):
                conn.execute(f"INSERT INTO immersion_sessions (date, title_text, medium_type) "
                             f"VALUES ('2026-01-0{i+1}', 'Test', 'anime')")

        migrations.migrate(v0_db, backup=False)
        with db.connect(v0_db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM immersion_sessions WHERE uuid IS NULL"
            ).fetchone()[0] == 0

    def test_identical_rows_get_distinct_uuids(self, tmp_path):
        """Bulk-imported rows share created_at, but the ordinal suffix should differentiate them."""
        v0_db = _make_v0_db(str(tmp_path / "old.db"))
        with db.connect(v0_db) as conn:
            for _ in range(2):
                conn.execute("""
                    INSERT INTO immersion_sessions (date, title_text, medium_type, created_at)
                    VALUES ('2026-01-01', 'Test Same', 'anime', '2026-01-01 10:00:00')
                """)

        migrations.migrate(v0_db, backup=False)
        with db.connect(v0_db) as conn:
            uuids = [r[0] for r in conn.execute("SELECT uuid FROM immersion_sessions")]
            assert len(set(uuids)) == 2

    def test_backfill_is_deterministic_across_databases(self, tmp_path):
        """Two copies of one ancestor should derive identical UUIDs"""
        def build_db(path):
            v0_db = _make_v0_db(str(path))

            with db.connect(v0_db) as conn:
                for _ in range(2):
                    conn.execute("""
                        INSERT INTO immersion_sessions (date, title_text, medium_type, created_at)
                        VALUES ('2026-01-01', 'Test Same', 'anime', '2026-01-01 10:00:00')
                    """)

            migrations.migrate(v0_db, backup=False)
            with db.connect(v0_db) as conn:
                return [r[0] for r in conn.execute("SELECT uuid FROM immersion_sessions")]

        assert build_db(tmp_path / "a.db") == build_db(tmp_path / "b.db")
