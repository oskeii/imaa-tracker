import pytest
from datetime import date, timedelta
import json
import db
import repo


# ==============================
# FIXTURES
# ==============================
@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Create a fresh database for each test."""
    test_db_path = tmp_path / "test.db"
    # monkeypatch DB_NAME for repo's db.get_connection() calls
    monkeypatch.setattr(db, "DB_NAME", str(test_db_path))
    db.init_db(str(test_db_path))
    yield str(test_db_path)


@pytest.fixture
def sample_title():
    """Create a single title and return its ID"""
    return repo.add_title("カードキャプターさくら", "anime")


@pytest.fixture
def sample_sessions(sample_title):
    """Create several sessions with varied data for testing queries"""
    today = date.today()
    sessions = [
        # Today: 2 anime sessions
        {
            "date_str": today.isoformat(), "medium_type": "anime", "activity_type": "listening",
            "title_id": sample_title, "title_text": "カードキャプターさくら",
            "duration_minutes": 40, "episode_count": 2, "episode_name": "ep.31-32"
        },
        {
            "date_str": today.isoformat(), "medium_type": "anime", "activity_type": "listening",
            "title_text": "からかい上手の高木さん",
            "duration_minutes": 20, "episode_count": 1, "episode_name": "ep.1"
        },
        # Yesterday: reading session
        {
            "date_str": (today - timedelta(days=1)).isoformat(),
            "medium_type": "light_novel", "activity_type": "reading", "title_text": "キノの旅",
            "duration_minutes": 66, "character_count": 3665, "volume": "vol.1", "chapter": "1-1"
        },
        # 3 days ago: VN session ("both" activity)
        {
            "date_str": (today - timedelta(days=3)).isoformat(),
            "medium_type": "visual_novel", "activity_type": "both", "title_text": "AMNESIA",
            "duration_minutes": 120, "character_count": 19500
        },
    ]
    ids = [repo.add_immersion_session(**s) for s in sessions]
    return ids


# ==============================
# TITLE TESTS
# ==============================
class TestTitles:

    def test_add_title(self):
        """Basic insert and retrieve"""
        title_id = repo.add_title("キノの旅", "light_novel", genre="slice-of-life, fantasy")
        assert title_id is not None
        assert title_id > 0

        titles = repo.get_all_titles()
        assert len(titles) == 1
        assert titles[0]["name"] == "キノの旅"
        assert titles[0]["medium_type"] == "light_novel"
        assert titles[0]["genre"] == "slice-of-life, fantasy"

    def test_get_all_titles_filter_by_medium(self):
        """Filtering should only return matching medium types"""
        repo.add_title("Anime Title", "anime")
        repo.add_title("LN Title", "light_novel")
        repo.add_title("Another Anime", "anime")

        anime_titles = repo.get_all_titles("anime")
        assert len(anime_titles) == 2
        assert all(t["medium_type"] == "anime" for t in anime_titles)

    def test_same_name_different_medium_are_distinct(self):
        """Re:Zero as anime and LN should be separate titles"""
        id1 = repo.add_title("Re:Zero", "anime")
        id2 = repo.add_title("Re:Zero", "light_novel")
        assert id1 != id2

        assert len(repo.get_all_titles()) == 2

    def test_get_or_create_title_existing(self):
        """Should return existing title ID without creating a duplicate"""
        id1 = repo.add_title("Test Title", "anime")
        id2 = repo.get_or_create_title("Test Title", "anime")
        assert id2 == id1

        assert len(repo.get_all_titles()) == 1

    def test_get_or_create_title_new(self):
        """Should create when title doesn't exist"""
        id1 = repo.get_or_create_title("New Title", "anime")
        titles = repo.get_all_titles()
        assert len(titles) == 1
        assert titles[0]["id"] == id1
        assert titles[0]["name"] == "New Title"


# ==============================
# IMMERSION SESSION TESTS
# ==============================
class TestImmersionSessions:

    def test_add_session_minimal(self):
        """A session only needs date, title_text, medium_type, and activity_type.
        (Duration may be forgotten and corrected later)"""
        session_id = repo.add_immersion_session(
            date_str="2026-04-01",
            title_text="Test Anime",
            medium_type="anime",
            activity_type="listening"
        )
        assert session_id is not None

        sessions = repo.get_immersion_sessions()
        assert len(sessions) == 1
        assert sessions[0]["title_text"] == "Test Anime"
        assert sessions[0]["date"] == "2026-04-01"
        assert sessions[0]["duration_minutes"] is None

    def test_add_session_full(self):
        """All fields should be stored and retrievable."""
        urls = json.dumps(["https://youtube.com/watch?v-abc123"])
        session_id = repo.add_immersion_session(
            date_str="2026-04-01",
            medium_type="youtube",
            activity_type="listening",
            title_text="Japanese Cooking Vlog",
            duration_minutes=34,
            character_count=None,
            reading_direction=None,
            volume=None,
            chapter=None,
            episode_name=None,
            urls_json=urls,
            notes="Interesting video about cooking",
        )

        sessions = repo.get_immersion_sessions()
        assert sessions[0]["urls_json"] == urls
        assert sessions[0]["notes"] == "Interesting video about cooking"
        assert sessions[0]["reading_direction"] is None

    def test_filter_by_date_range(self, sample_sessions):
        """Date filtering should be inclusive on both ends"""
        today = date.today()
        yesterday = (today - timedelta(days=1))
        sessions = repo.get_immersion_sessions(start_date=yesterday.isoformat(), end_date=today.isoformat())
        # All 3 sessions from yesterday and today
        assert len(sessions) == 3

    def test_filter_by_medium(self, sample_sessions):
        ln_sessions = repo.get_immersion_sessions(medium_type="light_novel")
        assert len(ln_sessions) == 1
        assert ln_sessions[0]["title_text"] == "キノの旅"

        anime_sessions = repo.get_immersion_sessions(medium_type="anime")
        assert len(anime_sessions) == 2

    def test_filter_by_activity(self, sample_sessions):
        sessions = repo.get_immersion_sessions(activity_type="both")
        assert len(sessions) == 1
        assert sessions[0]["title_text"] == "AMNESIA"

    def test_delete_session(self, sample_sessions):
        before = repo.get_immersion_sessions()
        assert len(before) == 4

        repo.delete_immersion_session(sample_sessions[0])

        after = repo.get_immersion_sessions()
        assert len(after) == 3

