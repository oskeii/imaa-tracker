"""Characterization tests for dashboard queries"""

from datetime import date, timedelta
import pytest

from imaa_tracker.core import repo

# A fixed week
MON = "2026-06-01"
TUE = "2026-06-02"
WED = "2026-06-03"
THU = "2026-06-04"
SUN = "2026-06-07"
NEXT_MON = "2026-06-08"
PREV_WEEK = "2026-05-27"
JULY = "2026-07-02"


@pytest.fixture()
def dataset():
    """
    Layout:
      MON  reading    60min   6000 chars   ln     (title 1)
      MON  listening  30min      0 chars   anime  (title 2)
      TUE  reading    90min   8000 chars   ln     (title 1)
      WED  reading    10min    500 chars   manga  (title 3)   <- under 15min
      THU  both       45min   6500 chars   vn     (quick-log, title_id NULL)
      SUN  listening  20min      0 chars   anime  (title 2)
      --- outside the week ---
      PREV_WEEK reading 100min 9500 chars ln     (title 1)
      JULY      reading  25min  1500 chars ln     (title 1)
    """
    ln = repo.add_title("キノの旅", "light_novel")
    anime = repo.add_title("からかい上手の高木さん", "anime")
    manga = repo.add_title("よつばと！", "manga")

    def add(d, medium, activity, mins, chars, title_id=None, **kw):
        return repo.add_immersion_session(
            d, "t", medium, activity,
            title_id=title_id, duration_minutes=mins,
            character_count=chars, **kw
        )

    add(MON, "light_novel", "reading", 60, 6000, ln)
    add(MON, "anime", "listening", 30, 0, anime, episode_count=2)
    add(TUE, "light_novel", "reading", 90, 8000, ln)
    add(WED, "manga", "reading", 10, 500, manga, page_count=20)
    add(THU, "visual_novel", "both", 45, 6500, None)
    add(SUN, "anime", "listening", 20, 0, anime, episode_count=1)
    add(PREV_WEEK, "light_novel", "reading", 100, 9500, ln)
    add(JULY, "light_novel", "reading", 25, 1500, ln)

    return {"ln": ln, "anime": anime, "manga": manga}


def test_fixture_week_starts_on_monday():
    assert date.fromisoformat(MON).weekday() == 0
    assert date.fromisoformat(SUN).weekday() == 6


class TestDailySummary:

    def test_daily_summary_totals(self, dataset):
        # MON: 2 sessions, 60 + 30 = 90 minutes, 6000 + 0 chars
        s = repo.get_daily_summary(MON)
        assert s["session_count"] == 2
        assert s["total_minutes"] == 90
        assert s["total_chars"] == 6000
        assert s["date"] == MON
        assert s["by_activity"] == {"reading": 60, "listening": 30}

    def test_daily_summary_defaults_to_today(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        repo.add_immersion_session(
            today.isoformat(), "t", "manga", "reading",
            duration_minutes=42
        )
        repo.add_immersion_session(
            yesterday.isoformat(), "t", "manga", "reading",
            duration_minutes=20
        )
        s = repo.get_daily_summary()
        assert s["date"] == today.isoformat()
        assert s["total_minutes"] == 42

    def test_daily_summary_empty_day_returns_zeros(self, dataset):
        """
        Day with no logs returns zeros (to be rendered in UI), not None
        """
        s = repo.get_daily_summary("2026-01-01")
        assert s["total_minutes"] == 0
        assert s["total_chars"] == 0
        assert s["session_count"] == 0
        assert s["by_activity"] == {}

    def test_daily_summary_omits_activities_with_no_sessions(self, dataset):
        """Daily summary does not include activities with no sessions in activity breakdown (unlike weekly summary)"""
        # TUE: only 1 (90 min) reading session
        s = repo.get_daily_summary(TUE)
        assert "listening" not in s["by_activity"]
        assert "both" not in s["by_activity"]
        assert s["by_activity"] == {"reading": 90}


class TestWeeklySummary:

    def test_weekly_summary_is_monday_to_sunday(self, dataset):
        # add a session of 40 min for the previous Sunday preceding MON
        prev_sun = repo.add_immersion_session(
            "2026-05-31", "T", "manga", "reading",
            duration_minutes=40, page_count=60
        )
        # the session for SUN is only 20 min
        # Total minutes will be 275 if prev_sun is included, 255 if it's the Sunday proceeding MON (SUN)
        s = repo.get_weekly_summary(WED)
        assert s["total_minutes"] == 255
        assert s["week_start"] == MON
        assert s["week_end"] == SUN

    def test_weekly_summary_any_weekday_gives_same_result(self, dataset):
        """week_of can be any date within the target week"""
        assert repo.get_weekly_summary(MON) == repo.get_weekly_summary(WED)
        assert repo.get_weekly_summary(MON) == repo.get_weekly_summary(SUN)

    def test_weekly_summary_totals(self, dataset):
        # In-week: 60+30+90+10+45+20 = 255 min; 6000+0+8000+500+6500+0 = 21000 chars
        # the two sessions of PREV_WEEK and JULY must be excluded.
        s = repo.get_weekly_summary(WED)
        assert s["total_minutes"] == 255
        assert s["total_chars"] == 21000
        assert s["session_count"] == 6
        assert s["by_activity"] == {"reading": 160, "listening": 50, "both": 45}

    def test_weekly_summary_defaults_to_current_week(self):
        today = date.today()
        this_monday = today - timedelta(days=today.weekday())
        repo.add_immersion_session(today.isoformat(), "t", "manga", "reading",
                                   duration_minutes=15)
        s = repo.get_weekly_summary()
        assert s["week_start"] == this_monday.isoformat()
        assert s["total_minutes"] == 15

    def test_weekly_summary_by_activity_has_all_three_keys(self, dataset):
        """Pre-seeded to zero. Empty dates still have full dictionary"""
        s = repo.get_weekly_summary("2026-01-01")
        assert s["by_activity"] == {"reading": 0, "listening": 0, "both": 0}

    def test_weekly_summary_daily_minutes_has_all_seven_days(self, dataset):
        """daily_minutes should include empty dates"""
        s = repo.get_weekly_summary(WED)
        daily_min = s["daily_minutes"]

        assert list(daily_min.keys()) == [
            (date.fromisoformat(MON) + timedelta(days=i)).isoformat()
            for i in range(7)
        ]
        assert daily_min[MON] == {"reading": 60, "listening": 30, "both": 0}
        assert daily_min[THU] == {"reading": 0, "listening": 0, "both": 45}
        # Nothing logged on Friday
        fri = (date.fromisoformat(THU) + timedelta(days=1)).isoformat()
        assert daily_min[fri] == {"reading": 0, "listening": 0, "both": 0}

    def test_weekly_summary_daily_avg_always_divides_by_seven(self):
        """
        Buggy: daily_avg divides by 7 unconditionally, including for the CURRENT week
        Results in a number that climbs all week for a reason unapparent to the user
        """
        today = date.today()
        mon = today - timedelta(days=today.weekday())
        repo.add_immersion_session(mon.isoformat(), "t", "anime", "listening",
                                   duration_minutes=20)
        repo.add_immersion_session(mon.isoformat(), "t", "light_novel", "reading",
                                   duration_minutes=50, character_count=4500)
        s1 = repo.get_weekly_summary(mon.isoformat())
        # minutes: 70/7 = 10, chars: 4500/7 = 643
        # reading: 50/7 = 7, listening = 20/7 = 3
        assert s1["daily_avg"] == {
            "minutes": 10, "chars": 643, "reading_minutes": 7, "listening_minutes": 3
        }

        wed = mon + timedelta(days=2)
        assert wed.weekday() == 2
        repo.add_immersion_session(wed.isoformat(), "t", "anime", "listening",
                                   duration_minutes=40)
        thu = mon + timedelta(days=3)
        repo.add_immersion_session(thu.isoformat(), "t", "light_novel", "reading",
                                   duration_minutes=70, character_count=8500)
        s2 = repo.get_weekly_summary(thu.isoformat())
        assert s2["week_start"] == s1["week_start"]
        assert s2["session_count"] > s1["session_count"]
        # minutes: (20+50+40+70)/7 = 180/7 = 26,    chars: (4500+8500)/7 = 13000/7 = 1857
        # reading: (50+70)/7 = 120/7 = 17,          listening = (20+40)/7 = 60/7 = 9
        assert s2["daily_avg"] == {
            "minutes": 26, "chars": 1857, "reading_minutes": 17, "listening_minutes": 9
        }


class TestAllTimeTotals:

    def test_alltime_totals(self, dataset):
        # Total of all 8 sessions:
        #       60+30+90+10+45+20+100+25 = 380 min
        #       6000 + 0 + 8000 + 500 + 6500 + 0 + 9500 + 1500 =32000 chars
        t = repo.get_alltime_totals()
        assert t["session_count"] == 8
        assert t["total_minutes"] == 380
        assert t["total_chars"] == 32000
        assert t["total_episodes"] == 3  # 2+1
        assert t["total_pages"] == 20
        assert t["by_activity"] == {"reading": 285, "listening": 50, "both": 45}
        assert t["first_session"] == PREV_WEEK
        assert t["last_session"] == JULY

    def test_alltime_active_days_apply_fifteen_minute_rule(self, dataset):
        """
        HAVING daily_minutes >= 15
        Daily totals: PREV_WEEK 100, MON 90, TUE 90, WED 10, THU 45, SUN 20, JULY 25
        -> WED (10 min) is the only day below the threshold.
        7 days with sessions, 6 qualify as "active".
        """
        t = repo.get_alltime_totals()
        assert t["active_days"] == 6

    def test_alltime_active_days_boundary_is_inclusive(self, dataset):
        """A day with exactly 15 minutes logged counts"""
        t_before = repo.get_alltime_totals()
        assert t_before["active_days"] == 6

        repo.add_immersion_session("2026-04-01", "t", "manga", "reading",
                                   duration_minutes=15)
        repo.add_immersion_session("2026-04-02", "t", "manga", "reading",
                                   duration_minutes=14)

        t = repo.get_alltime_totals()
        assert t["active_days"] == 7

    def test_alltime_active_days_qualifies_by_daily_total(self, dataset):
        """
        A day with two separate sessions both under 15 minutes,
        but totaling over 15 minutes counts as an "active" day
        """
        t_before = repo.get_alltime_totals()
        assert t_before["active_days"] == 6
        repo.add_immersion_session("2026-04-04", "t", "manga", "reading",
                                   duration_minutes=10)
        repo.add_immersion_session("2026-04-04", "t", "light_novel", "reading",
                                   duration_minutes=13)

        t = repo.get_alltime_totals()
        assert t["active_days"] == 7

    def test_alltime_days_since_start_is_logged_days(self, dataset):
        """
        Misleading name: days_since_start is COUNT(DISTINCT date)
        = the number of days ANYTHING was logged
        not the days elapsed since user's first session, or days between first and last session.

        Fixture spans 2026-05-27 to 2026-07-02: 36 calendar days.
        The function returns 7, because that's how many distinct dates have sessions.
        """
        t = repo.get_alltime_totals()
        assert t["days_since_start"] == 7

        elapsed_since_first = (date.fromisoformat(JULY) - date.fromisoformat(PREV_WEEK)).days + 1
        assert elapsed_since_first == 37
        assert t["days_since_start"] != elapsed_since_first

        elapsed_first_and_last = (date.today() - date.fromisoformat(PREV_WEEK)).days + 1
        assert t["days_since_start"] != elapsed_first_and_last

    def test_alltime_title_count_ignores_quick_logged_sessions(self, dataset):
        """
        BUGGY!: COUNT(DISTINCT title_id) excludes NULLs, title_id is NULL for quick-logged sessions.
        The fixture has 3 titles plus one quick-log (the visual novel), so this reports 3.
        This is just confusing from the user's perspective.
        !! Related to issue of repo.add_immersion_session() depending on GUI components
        to resolve/verify title_id with title_text.
        """
        t = repo.get_alltime_totals()
        assert t["title_count"] == 3

    def test_alltime_totals_on_empty_database(self):
        t = repo.get_alltime_totals()
        assert t["session_count"] == 0
        assert t["total_minutes"] == 0
        assert t["total_chars"] == 0
        assert t["total_episodes"] == 0
        assert t["total_pages"] == 0
        assert t["by_activity"] == {}
        # MIN/MAX over zero rows are NULL, and no COALESCE guards these two
        # so the dashboard must handle None as a possible result
        assert t["first_session"] is None
        assert t["last_session"] is None


class TestDailyTotals:

    def test_daily_totals_one_row_per_day_asc(self, dataset):
        rows = repo.get_daily_totals(MON, SUN)
        assert [r["date"] for r in rows] == [MON, TUE, WED, THU, SUN]
        assert rows[0] == {
            "date": MON, "total_minutes": 90, "total_chars": 6000, "session_count": 2
        }

    def test_daily_totals_skip_days_with_no_sessions(self, dataset):
        rows = repo.get_daily_totals(MON, SUN)
        assert len(rows) == 5
        assert "2026-06-05" not in [r["date"] for r in rows]

    def test_empty_window_returns_empty_list(self, dataset):
        assert repo.get_daily_totals("2022-01-01", "2022-01-31") == []


class TestActivityBreakdown:

    def test_activity_breakdown_by_month(self, dataset):
        # 1 session in May, 6 sessions in June, 1 session in July
        out = repo.get_activity_breakdown(PREV_WEEK, JULY, group_by="month")
        assert out["2026-05"] == {
            "reading": 100, "listening": 0, "both": 0, "session_count": 1
        }
        assert out["2026-06"] == {
            "reading": 160, "listening": 50, "both": 45, "session_count": 6
        }
        assert out["2026-07"] == {
            "reading": 25, "listening": 0, "both": 0, "session_count": 1
        }

    def test_activity_breakdown_by_week_starts_mondays(self, dataset):
        out = repo.get_activity_breakdown(PREV_WEEK, JULY, group_by="week")
        assert MON in out
        assert out[MON] == {
            "reading": 160, "listening": 50, "both": 45, "session_count": 6
        }
        assert "2026-05-25" in out  # the Monday of PREV_WEEK (PREV_WEEK value is a Wednesday)

    def test_activity_breakdown_unknown_group_by_collapses_to_alltime(self, dataset):
        """An unrecognized group_by argument gives a single all-time group, rather than an error."""
        out = repo.get_activity_breakdown(PREV_WEEK, JULY, group_by="quarter")
        assert list(out.keys()) == ["all-time"]
        assert out["all-time"]["session_count"] == 8

    def test_activity_breakdown_default_group_by_is_month(self, dataset):
        assert (repo.get_activity_breakdown(PREV_WEEK, JULY)
                == repo.get_activity_breakdown(PREV_WEEK, JULY, group_by="month"))

    def test_activity_breakdown_always_has_all_keys(self, dataset):
        out = repo.get_activity_breakdown(PREV_WEEK, JULY, group_by="month")
        for period in out.values():
            assert set(period) == {"reading", "listening", "both", "session_count"}


class TestTimeByMedium:

    def test_time_by_medium_ordered_by_minutes_desc(self, dataset):
        rows = repo.get_time_by_medium(MON, SUN)
        minutes = [r["total_minutes"] for r in rows]
        assert minutes == sorted(minutes, reverse=True)
        # most time spent on light novels
        assert rows[0] == {
            "medium_type": "light_novel", "total_minutes": 150, "session_count": 2
        }

    def test_time_by_medium_date_range_inclusive(self, dataset):
        rows = repo.get_time_by_medium(MON, MON)
        assert {r["medium_type"] for r in rows} == {"light_novel", "anime"}

    def test_time_by_medium_none_dates_returns_alltime_data(self, dataset):
        rows = repo.get_time_by_medium(None, None)
        ln = next(r for r in rows if r["medium_type"] == "light_novel")
        assert ln["total_minutes"] == 275  # 60+90+100+25

    def test_time_by_medium_ignores_activity_filter(self, dataset):
        """activity argument accepted, but not yet implemented"""
        unfiltered = repo.get_time_by_medium(MON, SUN)
        filtered = repo.get_time_by_medium(MON, SUN, activity="reading")
        assert filtered == unfiltered


class TestTimeByMediumMonthly:

    def test_time_by_medium_monthly_pivots_by_month(self, dataset):
        out = repo.get_time_by_medium_monthly(PREV_WEEK, JULY)
        assert set(out.keys()) == {"2026-05", "2026-06", "2026-07"}
        assert out["2026-05"]["light_novel"] == 100
        assert out["2026-06"]["light_novel"] == 150
        assert out["2026-07"]["light_novel"] == 25
        assert out["2026-06"]["anime"] == 50

    def test_time_by_medium_monthly_pads_all_mediums_with_zeros(self, dataset):
        out = repo.get_time_by_medium_monthly(PREV_WEEK, JULY)
        from imaa_tracker.core.constants import ENUMS
        assert set(out["2026-05"].keys()) == set(ENUMS["MEDIUM_TYPES"])
        assert out["2026-05"]["drama"] == 0

    def test_time_by_medium_monthly_empty_date_range_returns_empty_dict(self, dataset):
        """Only pads months with at least one entry"""
        assert repo.get_time_by_medium_monthly("2022-01-01", "2022-12-31") == {}

    def test_time_by_medium_monthly_ignores_activity_filter(self, dataset):
        """argument accepted, but filter unimplemented"""
        unfiltered = repo.get_time_by_medium_monthly(MON, SUN)
        filtered = repo.get_time_by_medium_monthly(MON, SUN, activity="reading")
        assert filtered == unfiltered


class TestReadingSpeed:

    def test_reading_speed_data_only_rows_with_both_metrics(self, dataset):
        """Requires both character_count > 0 and duration_minutes > 0"""
        repo.add_immersion_session(THU, "t", "light_novel", "reading",
                                   duration_minutes=0, character_count=6500)
        assert len(repo.get_immersion_sessions(PREV_WEEK, JULY)) == 9

        rows = repo.get_reading_speed_data(PREV_WEEK, JULY)
        assert len(rows) == 6  # excludes 2 sessions with character_count=0, and 1 session with duration_minutes=0
        assert all(r["character_count"] > 0 and r["duration_minutes"] > 0
                   for r in rows)

    def test_reading_speed_data_excludes_nulls_and_zeros(self, dataset):
        """Sessions with NULL chars and 0 chars should be omitted"""
        before = repo.get_reading_speed_data(PREV_WEEK, JULY)
        assert len(before) == 6
        repo.add_immersion_session(TUE, "t", "manga", "reading",
                                   duration_minutes=30, character_count=0)
        repo.add_immersion_session(WED, "t", "manga", "reading",
                                   duration_minutes=30, character_count=None)

        repo.add_immersion_session(THU, "t", "light_novel", "reading",
                                   duration_minutes=None, character_count=4500)
        repo.add_immersion_session(THU, "t", "light_novel", "reading",
                                   duration_minutes=0, character_count=4500)

        after = repo.get_reading_speed_data(PREV_WEEK, JULY)
        assert len(after) == len(before)

    def test_reading_speed_data_ordered_by_date(self, dataset):
        rows = repo.get_reading_speed_data(PREV_WEEK, JULY)
        dates = [r["date"] for r in rows]
        assert dates == sorted(dates)

    def test_reading_speed_data_date_range(self, dataset):
        rows = repo.get_reading_speed_data(MON, SUN)
        assert {r["date"] for r in rows} == {MON, TUE, WED, THU}
        assert PREV_WEEK not in {r["date"] for r in rows}

    def test_reading_speed_data_returns_columns_needed_by_chart(self, dataset):
        rows = repo.get_reading_speed_data(MON, SUN)
        assert set(rows[0]).issuperset({
            "date", "character_count", "duration_minutes",
            "reading_direction", "medium_type",
        })

