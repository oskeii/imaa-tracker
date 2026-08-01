import json
from datetime import date, timedelta
import pytest

import repo


# ==============================
# FIXTURES
# ==============================
@pytest.fixture
def sample_title():
    """Create a single title and return its ID"""
    return repo.add_title("カードキャプターさくら", "anime")


@pytest.fixture
def sample_sessions(sample_title):
    """Create several sessions with varied data for testing queries. Returns list of IDs"""
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


@pytest.fixture
def sample_titles():
    """Create multiple titles, with similarities in names. Returns list of title IDs"""
    def add(name, medium, **kwargs):
        return repo.add_title(name, medium, **kwargs)

    return [
        # "君" ("kimi") matches:
        #   total: 7, LN: 1, manga: 1, anime: 5
        add("君の名は", medium="anime"),
        add("君の膵臓をたべたい", medium="anime"),
        add("君の膵臓をたべたい", medium="light_novel"),
        add("四月は君の噓", medium="anime"),
        add("君に届け", medium="anime"),
        add("正反対な君と僕", medium="anime"),
        add("正反対な君と僕", medium="manga"),

        # "かぐや" ("kaguya") matches:
        #   total: 3, manga: 1, anime: 2
        # "姫" ("hime") matches:
        #   total: 2, anime: 2
        add("かぐや様は告らせたい", medium="anime"),
        add("かぐや様は告らせたい", medium="manga"),
        add("超かぐや姫", medium="anime"),
        add("もののけ姫", medium="anime"),

        # "猫" ("neko") matches:
        #     total: 2, anime: 2
        add("猫の恩返し", medium="anime"),
        add("泣きたい私は猫をかぶる", medium="anime"),

        # "恋" ("koi")
        #     total: 5, manga: 2, anime: 3
        add("中二病でも恋がしたい", medium="anime"),
        add("山田くんとLv999の恋をする", medium="anime"),
        add("山田くんとLv999の恋をする", medium="manga"),
        add("ヲタクに恋は難しい", medium="anime"),
        add("ヲタクに恋は難しい", medium="manga"),

        # "さくら" ("sakura")
        #     total: 2, anime: 2
        add("カードキャプターさくら", medium="anime"),
        add("さくら荘のペットな彼女", medium="anime"),

        # "ゲーム" ("geemu")
        #     total: 3, LN: 1, manga: 1, anime: 1
        add("ノーゲーム・ノーライフ", medium="anime"),
        add("ノーゲーム・ノーライフ", medium="light_novel"),
        add("ダーウィンズゲーム", medium="manga"),

        # "戦記" ("senki")
        #     total: 3, manga: 1, anime: 2
        add("幼女戦記", medium="anime"),
        add("アルスラーン戦記", medium="anime"),
        add("アルスラーン戦記", medium="manga"),

        # "nana" matches: (will not match romaji/hiragana/katakana/kanji)
        #   "なな": 0
        #   "ナナ": 2 (1 manga, 1 anime)
        #   "七": 1 (anime)
        #   "nana": 1 (anime)

        add("七つの大罪", medium="anime"),
        add("無能のナナ", medium="anime"),
        add("無能のナナ", medium="manga"),
        add("NANA", medium="anime"),
    ]


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
        assert len(repo.get_all_titles("light_novel")) == 1
        assert len(repo.get_all_titles("drama")) == 0

    @pytest.mark.parametrize("query,medium_type,expected", [
        # --- "君" (kimi): 7 total; anime 5, manga 1, light_novel 1 ---
        ("君", None, 7),
        ("君", "anime", 5),
        ("君", "manga", 1),
        ("君", "light_novel", 1),
        ("君の", None, 4),           # narrower substring drops 正反対な君と僕 (×2) and 君に届け

        # --- kaguya / hime cluster ---
        ("かぐや", None, 3),          # かぐや様(×2) + 超かぐや姫
        ("姫", None, 2),             # 超かぐや姫, もののけ姫 (both anime)
        ("かぐや姫", None, 1),         # only 超かぐや姫 has both substrings adjacent
        ("姫", "manga", 0),          # filter zeroes out: 姫 titles are all anime

        # --- koi ---
        ("恋", None, 5),
        ("恋", "manga", 2),

        # --- geemu (suffix + infix) ---
        ("ゲーム", None, 3),
        ("ノーゲーム", None, 2),        # ダーウィンズゲーム drops out (ノー not present)

        # --- senki (suffix match) ---
        ("戦記", None, 3),           # 幼女戦記, アルスラーン戦記 ×2
        ("戦記", "anime", 2),

        # --- single-cluster sanity ---
        ("猫", None, 2),
        ("さくら", None, 2),

        # --- writing-system boundaries: "nana" is NOT cross-script ---
        ("七", None, 1),            # 七つの大罪
        ("ナナ", None, 2),           # 無能のナナ ×2 (katakana)
        ("なな", None, 0),           # hiragana matches nothing — LIKE is not kana-insensitive
        ("nana", None, 1),          # ASCII, lowercase -> matches "NANA" (LIKE IS ASCII-case-insensitive)
        ("NANA", None, 1),          # ASCII, exact case -> same single match

        # --- edge cases ---
        ("", None, 20),             # empty query -> %%  matches all 30, but LIMIT 20 caps it
        ("ゾンビ", None, 0),          # absent substring -> no matches

    ])
    def test_search_titles(self, sample_titles, query, medium_type, expected):
        """Substring search should match partial names"""
        results = repo.search_titles(query, medium_type=medium_type)
        assert len(results) == expected

    def test_search_titles_ordered_by_name(self, sample_titles):
        queries = [
            "記",  # アルスラーン戦記 ×2, 幼女戦記
            "ゲーム"  # ダーウィンズゲーム, ノーゲーム・ノーライフ ×2
        ]
        for q in queries:
            results = repo.search_titles(q)
            names = [r["name"] for r in results]
            assert names == sorted(names)

    def test_search_titles_like_wildcards_not_escaped(self, sample_titles):
        """
        (Characterization)
        query is interpolated into %{query}% without escaping LIKE metacharacters.
        '_' and '%' act as wildcards rather than literals; both match every title
        """
        assert len(repo.search_titles('_')) == 20
        assert len(repo.search_titles('%')) == 20

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

    def test_same_name_different_medium_are_distinct(self):
        """Re:Zero as anime and LN should be separate titles"""
        id1 = repo.add_title("Re:Zero", "anime")
        id2 = repo.add_title("Re:Zero", "light_novel")
        assert id1 != id2

        assert len(repo.get_all_titles()) == 2


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
        assert sessions[0]["title_id"] is None

    def test_add_session_full(self):
        """All fields should be stored and retrievable."""
        urls = json.dumps(["https://youtube.com/watch?v=abc123"])
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

    def test_get_session_by_id(self, sample_sessions):
        sessions = repo.get_immersion_sessions()
        for s in sessions[:3]:
            sid = s["id"]
            session_by_id = repo.get_immersion_session_by_id(sid)
            assert session_by_id["id"] == s["id"]
            assert session_by_id["date"] == s["date"]
            assert session_by_id["duration_minutes"] == s["duration_minutes"]
            assert session_by_id["title_text"] == s["title_text"]
            assert session_by_id["created_at"] == s["created_at"]

    def test_filter_by_date_range(self, sample_sessions):
        """Date filtering should be inclusive on both ends"""
        today = date.today()
        yesterday = (today - timedelta(days=1))
        valid_dates = (today.isoformat(), yesterday.isoformat())
        sessions = repo.get_immersion_sessions(start_date=yesterday.isoformat(), end_date=today.isoformat())
        # All 3 sessions from yesterday and today
        assert len(sessions) == 3
        assert sessions[0]["date"] in valid_dates
        assert sessions[1]["date"] in valid_dates
        assert sessions[2]["date"] in valid_dates

    def test_filter_after_start_date(self, sample_sessions):
        """Should return all sessions occurring on/after start_date (no end_date filter)"""
        today = date.today()
        yesterday = (today - timedelta(days=1))
        valid_dates = (today.isoformat(), yesterday.isoformat())
        sessions = repo.get_immersion_sessions(start_date=yesterday.isoformat())
        # All 3 sessions from yesterday and today
        assert len(sessions) == 3
        assert sessions[0]["date"] in valid_dates
        assert sessions[1]["date"] in valid_dates
        assert sessions[2]["date"] in valid_dates

    def test_filter_before_end_date(self, sample_sessions):
        """Should return all sessions occurring on/before end_date (no start_date filter)"""
        today = date.today()
        yesterday = (today - timedelta(days=1))
        valid_dates = (
            yesterday.isoformat(),
            (today - timedelta(days=3)).isoformat()
        )
        sessions = repo.get_immersion_sessions(end_date=yesterday.isoformat())
        # All 2 sessions from yesterday
        assert len(sessions) == 2
        assert sessions[0]["date"] in valid_dates
        assert sessions[1]["date"] in valid_dates

    def test_filter_by_medium(self, sample_sessions):
        ln_sessions = repo.get_immersion_sessions(medium_type="light_novel")
        assert len(ln_sessions) == 1
        assert ln_sessions[0]["title_text"] == "キノの旅"

        anime_sessions = repo.get_immersion_sessions(medium_type="anime")
        assert len(anime_sessions) == 2

        drama_sessions = repo.get_immersion_sessions(medium_type="drama")
        assert len(drama_sessions) == 0

    def test_filter_by_activity(self, sample_sessions):
        both = repo.get_immersion_sessions(activity_type="both")
        assert len(both) == 1
        assert both[0]["title_text"] == "AMNESIA"

        listening = repo.get_immersion_sessions(activity_type="listening")
        assert len(listening) == 2
        assert listening[0]["medium_type"] == "anime"
        assert listening[1]["medium_type"] == "anime"

    def test_sessions_ordered_by_date_desc(self, sample_sessions):
        """Most recent sessions listed first"""
        sessions = repo.get_immersion_sessions()
        dates = [s["date"] for s in sessions]
        assert dates == sorted(dates, reverse=True)

    def test_delete_session(self, sample_sessions):
        before = repo.get_immersion_sessions()
        assert len(before) == 4

        sid_to_del = 2
        before_ids = [s["id"] for s in before]
        assert sid_to_del in before_ids

        repo.delete_immersion_session(sid_to_del)

        after = repo.get_immersion_sessions()
        assert len(after) == 3
        after_ids = [s["id"] for s in after]
        assert sid_to_del not in after_ids

    class TestSessionEdits:
        """Updates and bulk operations on immersion_sessions"""

        def test_update_single_field(self, sample_sessions):
            """Updating a single field leaves all others untouched"""
            session_id = sample_sessions[0]
            before = repo.get_immersion_session_by_id(session_id)

            repo.update_immersion_session(session_id, duration_minutes=99)
            after = repo.get_immersion_session_by_id(session_id)
            assert after["duration_minutes"] == 99
            # Verify other fields unchanged
            assert after["title_text"] == before["title_text"]
            assert after["medium_type"] == before["medium_type"]
            assert after["activity_type"] == before["activity_type"]
            assert after["created_at"] == before["created_at"]

        def test_update_multiple_fields(self, sample_sessions):
            session_id = sample_sessions[0]
            before = repo.get_immersion_session_by_id(session_id)

            repo.update_immersion_session(
                session_id,
                duration_minutes=60,
                notes="updated note",
                activity_type="reading",
            )
            after = repo.get_immersion_session_by_id(session_id)
            assert after["duration_minutes"] == 60
            assert after["activity_type"] == "reading"
            assert after["notes"] == "updated note"
            # Verify other fields unchanged
            assert after["medium_type"] == before["medium_type"]
            assert after["title_text"] == before["title_text"]
            assert after["created_at"] == before["created_at"]

        def test_update_to_null(self, sample_sessions):
            """Setting a field to None should null the DB"""
            session_id = sample_sessions[2]
            before_char_count = repo.get_immersion_session_by_id(session_id)["character_count"]
            repo.update_immersion_session(session_id, character_count=before_char_count+500)
            after_change = repo.get_immersion_session_by_id(session_id)
            assert after_change["character_count"] == before_char_count + 500

            repo.update_immersion_session(session_id, character_count=None)
            after_null = repo.get_immersion_session_by_id(session_id)
            assert after_null["character_count"] is None

        def test_update_ignores_unknown_fields(self, sample_sessions):
            """Only valid/known fields are updated. Anything else is ignored, without throwing errors."""
            session_id = sample_sessions[0]
            before = repo.get_immersion_session_by_id(session_id)

            repo.update_immersion_session(
                session_id,
                duration_minutes=43,
                id=999,                             # ignored, cannot be overwritten
                this_field_is_made_up="abc123",     # ignored, no such field
            )
            after = repo.get_immersion_session_by_id(session_id)
            assert after["id"] == session_id
            assert after["duration_minutes"] == 43

            assert after["title_text"] == before["title_text"]
            assert after["created_at"] == before["created_at"]

        def test_update_with_no_valid_fields_is_ignored(self, sample_sessions):
            """If no valid fields passed, update should do nothing (not crash)"""
            session_id = sample_sessions[0]
            before = repo.get_immersion_session_by_id(session_id)

            repo.update_immersion_session(
                session_id,
                this_field_is_made_up="abc123",     # ignored, no such field
                its_my_birthday=False
            )
            after = repo.get_immersion_session_by_id(session_id)
            assert dict(after) == dict(before)

        def test_bulk_update_applies_to_all(self, sample_sessions):
            ids = sample_sessions[:3]
            count = repo.bulk_update_immersion_sessions(
                ids, activity_type="both", notes="batch updated"
            )
            assert count == 3

            updated = [repo.get_immersion_session_by_id(i) for i in ids]
            assert all(s["activity_type"] == "both" for s in updated)
            assert all(s["notes"] == "batch updated" for s in updated)

        def test_bulk_update_other_sessions_unaffected(self, sample_sessions):
            """Sessions not in the ID list are left untouched"""
            if len(sample_sessions) < 2:
                pytest.skip("Need at least 2 sample sessions")
            target_id = sample_sessions[0]
            other_id = sample_sessions[1]
            other_before = repo.get_immersion_session_by_id(other_id)

            repo.bulk_update_immersion_sessions([target_id], notes="this is the target")

            other_after = repo.get_immersion_session_by_id(other_id)
            assert other_after["notes"] == other_before["notes"]

        def test_bulk_update_empty_list(self, sample_sessions):
            before_notes = [s["notes"] for s in repo.get_immersion_sessions()]
            count = repo.bulk_update_immersion_sessions([], notes="X")
            assert count == 0

            after_notes = [s["notes"] for s in repo.get_immersion_sessions()]
            assert after_notes == before_notes

        def test_bulk_update_empty_fields(self, sample_sessions):
            count = repo.bulk_update_immersion_sessions(sample_sessions, hello="X")
            assert count == 0

        def test_bulk_delete(self, sample_sessions):
            before = repo.get_immersion_sessions()
            to_delete = sample_sessions[:2]

            count = repo.bulk_delete_immersion_sessions(to_delete)
            assert count == 2

            after = repo.get_immersion_sessions()
            assert len(after) == len(before) - 2
            remaining_ids = {s["id"] for s in after}
            assert remaining_ids.isdisjoint(to_delete)

        def test_bulk_delete_empty_list(self, sample_sessions):
            before_count = len(repo.get_immersion_sessions())
            count = repo.bulk_delete_immersion_sessions([])
            after_count = len(repo.get_immersion_sessions())
            assert count == 0
            assert after_count == before_count
