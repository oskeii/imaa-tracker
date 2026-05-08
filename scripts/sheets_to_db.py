"""
Migrate data from Immersion_Log.xlsx into the SQLite database.

Usage:
    python sheets_to_db.py [path_to_immersion_log]
"""

import sys
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

from db import (
    get_connection, init_db, DB_NAME,
)

# map old spreadsheet medium names to new medium_type values
LEGACY_MEDIUM_MAP = {
    "Anime": "anime",
    "Visual Novel": None,
    "Light Novel": "light_novel",
    "Book": None,
    "Manga": "manga",
    "Youtube": None,
    "Others": None,
    # "1": "drama",
    # "4": "podcast",
    # "5": "audiobook",
    # "2": "novel",
    # "3": "game",
}
stashed_rows = []


def is_monthly_sheet(name: str, start_year: int, end_year: int) -> bool:
    if not bool(re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4}$', name)):
        return False
    year = int(str(name).split('-')[1])
    if year < start_year or year > end_year:
        print(f"SKIPPING YEAR ({year}): {name}")
        return False
    return True


def guess_activity_type(medium: str) -> str:
    listening = {"anime", "drama", "podcast", "audiobook", "youtube"}
    reading = {"light_novel", "novel", "book", "manga"}
    if medium in listening:
        return "listening"
    if medium in reading:
        return "reading"
    return "both"  # visual_novel, game


def parse_duration_to_minutes(val) -> int:
    """Parse various duration formats into minutes."""
    if val is None or (isinstance(val, float) and str(val) == 'nan'):
        return 0
    if isinstance(val, timedelta):
        return round(val.total_seconds() / 60)
    if isinstance(val, datetime):
        return round((val.hour * 3600 + val.minute * 60 + val.second) / 60)
    s = str(val).strip()
    if not s or s == '0:00:00':
        return 0
    parts = s.split(':')
    try:
        if len(parts) == 3:
            return round((int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) / 60)
        if len(parts) == 2:
            return round((int(parts[0]) * 60 + int(parts[1])) / 60)
    except ValueError:
        pass
    return 0


def parse_detail_fields(title_text: str, medium: str) -> dict:
    details = {}
    if not isinstance(title_text, str):
        return details
    ep_match = re.search(r'ep\.?\s*(\S+)', title_text, re.IGNORECASE)
    if ep_match:
        details['episode_name'] = f"ep.{ep_match.group(1)}"
    ch_match = re.search(r'ch\.?\s*(\S+)', title_text, re.IGNORECASE)
    if ch_match:
        details['chapter'] = ch_match.group(1)
    vol_match = re.search(r'vol\.?\s*(\S+)', title_text, re.IGNORECASE)
    if vol_match:
        details['volume'] = f"Vol. {vol_match.group(1)}"
    if medium == 'light_novel' and 'chapter' not in details:
        sec_match = re.search(r'\s(\d+-\d+)\s*$', title_text)
        if sec_match:
            details['chapter'] = sec_match.group(1)
    return details


def clean_title(title_text: str) -> str:
    if not isinstance(title_text, str):
        return title_text
    cleaned = title_text.strip()
    cleaned = re.sub(r'\s+ep\.?\s*\S+\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+ch\.?\s*\S+\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+vol\.?\s*\S+\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+\d+-\d+\s*$', '', cleaned)
    return cleaned.strip()


def migrate_immersion_log(xlsx_path: str, conn: sqlite3.Connection) -> int:
    xls = pd.ExcelFile(xlsx_path)
    monthly_sheets = [s for s in xls.sheet_names if is_monthly_sheet(s, 2024, 2026)]
    print(f"Found {len(monthly_sheets)} monthly sheets to import.")

    if input("Would you like to check the monthly sheets found? (Y/N):") == "Y":
        print(monthly_sheets)
        input("Press Enter to continue:")

    title_cache = {}  # (clean_name, medium) -> title_id
    cur = conn.cursor()
    total_rows = 0

    for sheet_name in monthly_sheets:
        df = pd.read_excel(xls, sheet_name, header=None, usecols=list(range(7)))
        df = df.dropna(how="all")
        print(f"{sheet_name} DATAFRAME:\n{df.head()}")

        if len(stashed_rows) == 0:
            stashed_rows.append(df.iloc[0])
        for i in range(1, len(df)):
            row = df.iloc[i]
            date_val, title_text, medium_raw = row.iloc[0], row.iloc[1], row.iloc[2]
            char_count, episode_raw, page_count, duration_raw = row.iloc[3], row.iloc[4], row.iloc[5], row.iloc[6]

            # separate out data that needs to be confirmed and manually logged:
            # medium == VN ,others, book, youtube
            # medium or date or title is empty
            # title contains "misc."
            if pd.isna(date_val) or pd.isna(medium_raw) or pd.isna(title_text) or "misc" in str(title_text).strip():
                print(f"[EMPTY FIELD] Stashing row {i} of {sheet_name}")
                stashed_rows.append(row)
                continue

            # Parse date
            if isinstance(date_val, datetime):
                date_str = date_val.strftime('%Y-%m-%d')
            elif isinstance(date_val, str):
                date_str = date_val[:10]
            else:
                print(f"[DATE] Stashing row {i} of {sheet_name}")
                stashed_rows.append(row)
                continue

            # Map medium
            medium_str = str(medium_raw).strip() if pd.notna(medium_raw) else "Others"
            if medium_str in ["Youtube", "Visual Novel", "Book", "Others"]:
                print(f"[MEDIUM TYPE] Stashing row {i} of {sheet_name}")
                stashed_rows.append(row)
                continue

            medium_type = LEGACY_MEDIUM_MAP.get(medium_str)
            activity_type = guess_activity_type(medium_type)

            # Parse metrics
            duration_min = parse_duration_to_minutes(duration_raw)
            chars = int(char_count) if pd.notna(char_count) and char_count != 0 else None
            eps = int(episode_raw) if pd.notna(episode_raw) and episode_raw != 0 else None
            pages = int(page_count) if pd.notna(page_count) and page_count != 0 else None

            title_str = str(title_text).strip() if pd.notna(title_text) else None
            details = parse_detail_fields(title_str, medium_type) if title_str else {}
            base_title = clean_title(title_str) if title_str else None

            # Upsert title
            title_id = None
            if base_title:
                cache_key = (base_title, medium_type)
                if cache_key not in title_cache:
                    cur.execute(
                        "INSERT INTO titles (name, medium_type) VALUES (?, ?)",
                        (base_title, medium_type)
                    )
                    title_cache[cache_key] = cur.lastrowid
                title_id = title_cache[cache_key]

            cur.execute("""
                INSERT INTO immersion_sessions
                (date, title_id, title_text, medium_type, activity_type,
                 duration_minutes, character_count, page_count, episode_count,
                 volume, chapter, episode_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str, title_id, base_title, medium_type, activity_type,
                duration_min, chars, pages, eps,
                details.get('volume'), details.get('chapter'), details.get('episode_name'),
            ))
            total_rows += 1

    conn.commit()
    return total_rows


def print_summary(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("\n--- Import Summary ---")

    cur.execute("SELECT COUNT(*) FROM titles")
    print(f"  Titles:             {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM immersion_sessions")
    print(f"  Immersion sessions: {cur.fetchone()[0]}")

    cur.execute("""SELECT medium_type, COUNT(*) AS c FROM immersion_sessions
                   GROUP BY medium_type ORDER BY c DESC""")
    print("  By medium:")
    for row in cur.fetchall():
        print(f"    {row[0]:15s} {row[1]}")

    cur.execute("SELECT MIN(date), MAX(date) FROM immersion_sessions WHERE date <= date('now')")
    row = cur.fetchone()
    print(f"  Date range:         {row[0]} → {row[1]}")

    cur.execute("SELECT SUM(duration_minutes) FROM immersion_sessions")
    total_min = cur.fetchone()[0] or 0
    print(f"  Total immersion:    {total_min} min ({total_min/60:.1f} hours)")


def main():
    immersion_path = sys.argv[1] if len(sys.argv) > 1 else "Immersion_Log.xlsx"

    while not Path(immersion_path).exists():
        print(f"Error: {immersion_path} not found")
        immersion_path = input("""Please enter the path (including extension) of your Immersion Log spreadsheet
            (or type 'X' to exit)\n""")
        if immersion_path.upper() == "X":
            sys.exit(1)

    print("Initializing database...")
    init_db()
    conn = get_connection()

    print(f"Importing immersion log from {immersion_path}...")
    n = migrate_immersion_log(immersion_path, conn)
    print(f"  Imported {n} immersion sessions.")

    print_summary(conn)
    conn.close()
    print(f"\nDone! Database saved to: {DB_NAME}")

    # Output stashed rows as CSV for user to log manually
    if stashed_rows:
        stash_df = pd.DataFrame(stashed_rows)
        stash_df.to_csv('stashed_entries.csv', index=False, header=False)
        stash_df.to_csv('stashed_entries_(utf8-sig).csv', encoding="utf-8-sig", index=False, header=False)
        print(f"""
            {len(stash_df)-1} entries have been added to 'stashed_entries.csv'
            Please check and manually log these in the app.""")
    else:
        print("No entries were stashed. You're all set!")


if __name__ == "__main__":
    main()
