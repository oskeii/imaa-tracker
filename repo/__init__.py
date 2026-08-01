"""Repository package -- all the application's SQL queries here."""

from .titles import (
    get_all_titles,
    search_titles,
    add_title,
    get_or_create_title,
)

from .sessions import (
    add_immersion_session,
    get_immersion_sessions,
    get_immersion_session_by_id,
    update_immersion_session,
    delete_immersion_session,
    bulk_update_immersion_sessions,
    bulk_delete_immersion_sessions,
)

from .stats import (
    get_daily_summary,
    get_weekly_summary,
    get_alltime_totals,
    get_activity_breakdown,
    get_daily_totals,
    get_reading_speed_data,
    get_time_by_medium,
    get_time_by_medium_monthly,
)
