"""
Generator for demo.json — a realistic 18-month Japanese learning journey.

Run this to produce demo.json with dynamic dates (days_ago offsets).
The migration script (demo_to_db.py) converts those to actual dates at import time,
so re-running in the future still produces a database with current activity.
"""

import json
import random
from typing import Any

random.seed(42)  # reproducible output


# ────────────────────────────────────────────
#  TITLES
# ────────────────────────────────────────────

TITLES = [
    # ── Anime ──
    {"name": "カードキャプターさくら", "medium_type": "anime",
     "genre": "magical girl, fantasy", "tags": "classic, easy",
     "api": "anilist", "api_id": "232",
     "notes": "Started as a beginner — slow pace, clear pronunciation."},
    {"name": "からかい上手の高木さん", "medium_type": "anime",
     "genre": "romance, slice of life", "tags": "easy, daily life vocab",
     "api": "anilist", "api_id": "98568"},
    {"name": "夏目友人帳", "medium_type": "anime",
     "genre": "supernatural, slice of life", "tags": "iyashikei",
     "api": "anilist", "api_id": "4081"},
    {"name": "ゆるキャン△", "medium_type": "anime",
     "genre": "slice of life, outdoor", "tags": "iyashikei, easy",
     "api": "anilist", "api_id": "98444"},
    {"name": "鬼滅の刃", "medium_type": "anime",
     "genre": "action, supernatural", "tags": "shonen, popular",
     "api": "anilist", "api_id": "101922"},
    {"name": "リコリス・リコイル", "medium_type": "anime",
     "genre": "action", "tags": "girls with guns",
     "api": "anilist", "api_id": "150672"},
    {"name": "薬屋のひとりごと", "medium_type": "anime",
     "genre": "mystery, historical", "tags": "harder vocab, classical",
     "api": "anilist", "api_id": "161645"},

    # ── Manga ──
    {"name": "よつばと！", "medium_type": "manga",
     "genre": "slice of life, comedy", "tags": "beginner, daily life",
     "api": "anilist", "api_id": "30105",
     "notes": "First manga ever completed — perfect for beginners."},
    {"name": "ゆるキャン△", "medium_type": "manga",
     "genre": "slice of life, outdoor",
     "api": "anilist", "api_id": "86464"},
    {"name": "鬼滅の刃", "medium_type": "manga",
     "genre": "action, supernatural",
     "api": "anilist", "api_id": "87216"},
    {"name": "化物語", "medium_type": "manga",
     "genre": "supernatural, mystery", "tags": "wordplay heavy",
     "api": "anilist", "api_id": "85973"},

    # ── Light Novels ──
    {"name": "キノの旅", "medium_type": "light_novel",
     "genre": "fantasy, philosophical", "tags": "short stories, beginner friendly",
     "api": "anilist", "api_id": "7723",
     "notes": "First LN. Vertical text. Self-contained chapters help with comprehension."},
    {"name": "涼宮ハルヒの憂鬱", "medium_type": "light_novel",
     "genre": "sci-fi, comedy", "tags": "intermediate",
     "api": "anilist", "api_id": "10080"},
    {"name": "響け！ユーフォニアム", "medium_type": "light_novel",
     "genre": "drama, music", "tags": "music vocab",
     "api": "anilist", "api_id": "18887"},
    {"name": "ノーゲーム・ノーライフ", "medium_type": "light_novel",
     "genre": "fantasy, isekai", "tags": "complex vocab",
     "api": "anilist", "api_id": "20586"},

    # ── Visual Novels ──
    {"name": "CLANNAD", "medium_type": "visual_novel",
     "genre": "romance, drama", "tags": "fully voiced, classic",
     "api": "vndb", "api_id": "v4"},

    # ── Games ──
    {"name": "ペルソナ4 ゴールデン", "medium_type": "game",
     "genre": "rpg, mystery", "tags": "fully voiced, modern setting",
     "api": "igdb", "api_id": "2462"},

    # ── YouTube ──
    {"name": "日本語の森", "medium_type": "youtube",
     "genre": "study", "tags": "grammar, jlpt",
     "youtube_channel_id": "UC2lwm22FaOpbJ7vS6WuLuyA",
     "youtube_url": "https://www.youtube.com/@nihongonomori2013",
     "notes": "Grammar explanations in Japanese. Great for N3+."},
    {"name": "Yuyu's Japanese Tutor", "medium_type": "youtube",
     "genre": "study", "tags": "comprehensible input",
     "youtube_channel_id": "UCpnkCq0Vz_4kahmlmrXuhrA",
     "youtube_url": "https://www.youtube.com/@YuyutheTutor"},
    {"name": "Native Japanese Vlogs", "medium_type": "youtube",
     "genre": "vlogs", "tags": "natural speech",
     "notes": "Various channels — daily life vlogs."},

    # ── Audiobook ──
    {"name": "コンビニ人間 (Audiobook)", "medium_type": "audiobook",
     "genre": "literary fiction", "tags": "modern, intermediate"},
]


# ────────────────────────────────────────────
#  RESOURCES
# ────────────────────────────────────────────

RESOURCES = [
    {"name": "Genki II", "resource_type": "textbook", "level": "beginner",
     "notes": "Completed during first 6 months."},
    {"name": "Tobira", "resource_type": "textbook", "level": "intermediate",
     "notes": "Ongoing — chapter 8 currently."},
    {"name": "Anki — Core 2k/6k", "resource_type": "app", "level": "beginner",
     "url": "https://ankiweb.net"},
    {"name": "Anki — Kaishi 1.5k", "resource_type": "app", "level": "beginner"},
    {"name": "Anki — Mining Deck (personal)", "resource_type": "app", "level": "intermediate"},
    {"name": "Bunpro", "resource_type": "app", "level": "N4",
     "url": "https://bunpro.jp"},
    {"name": "日本語の森 N4 Mock", "resource_type": "mock_exam", "level": "N4"},
    {"name": "日本語の森 N3 Mock", "resource_type": "mock_exam", "level": "N3"},
    {"name": "Cure Dolly — Organic Japanese", "resource_type": "video_course",
     "level": "beginner",
     "url": "https://www.youtube.com/@organicjapanesewithcuredolly9614"},
]


# ────────────────────────────────────────────
#  SESSION GENERATION
# ────────────────────────────────────────────
#
# Strategy: define a learning timeline with phases. For each phase,
# specify which titles are active and at what pace. Generate sessions
# that reflect plausible progression — chapters/episodes advance,
# reading speed slowly improves.

def gen_session(days_ago: int, title: str, medium_type: str,
                activity_type: str, duration: int,
                **extra) -> dict[str, Any]:
    s = {
        "days_ago": days_ago,
        "title": title,
        "medium_type": medium_type,
        "activity_type": activity_type,
        "duration_minutes": duration,
    }
    s.update(extra)
    return s


sessions: list[dict] = []


# ── Phase 1: Early days (540-360 days ago) ──
# Beginner. Lots of anime, some manga. Building habit.
# ~70 sessions over 180 days = roughly every 2.5 days
def gen_phase1():
    # CCS anime — main early activity, ~50 episodes watched
    for i in range(50):
        day = 540 - i * 3 - random.randint(0, 2)
        ep = i + 1
        # Sometimes 2 episodes in one session
        ep_count = random.choices([1, 2], weights=[7, 3])[0]
        duration = 22 * ep_count + random.randint(-3, 5)
        sessions.append(gen_session(
            day, "カードキャプターさくら", "anime", "listening",
            duration,
            episode_count=ep_count,
            episode_name=f"ep.{ep}" if ep_count == 1 else f"ep.{ep}-{ep + 1}",
        ))

    # Yotsuba manga — first manga reads, slow
    yotsuba_chapters = 30
    for i in range(yotsuba_chapters):
        day = 530 - i * 5 - random.randint(0, 3)
        if day < 360:
            break
        pages = random.randint(20, 35)
        chars = pages * random.randint(80, 130)  # ~100 chars/page for easy manga
        duration = random.randint(15, 35)
        sessions.append(gen_session(
            day, "よつばと！", "manga", "reading", duration,
            page_count=pages,
            character_count=chars,
            chapter=f"ch.{i + 1}",
            volume=f"Vol. {(i // 6) + 1}",
            reading_direction="vertical",
        ))

    # Some early YouTube study viewing
    for i in range(15):
        day = random.randint(360, 540)
        ch = random.choice(["Yuyu's Japanese Tutor", "日本語の森"])
        duration = random.randint(10, 25)
        sessions.append(gen_session(
            day, ch, "youtube", "listening", duration,
        ))


# ── Phase 2: Intermediate (360-180 days ago) ──
# Started LNs. More consistent. ~120 sessions over 180 days.
def gen_phase2():
    # Kino's Journey — first LN. Vertical reading.
    # Reading speed improves over time: starts ~1000 chars/hr, ends ~1600
    kino_sessions = 40
    for i in range(kino_sessions):
        day = 355 - i * 4 - random.randint(0, 2)
        if day < 180:
            break
        chars = random.randint(1500, 3000)
        chars_per_hour = 1000 + i * 15
        duration = int(chars / chars_per_hour * 60) + random.randint(-3, 5)
        duration = max(duration, 15)
        vol_num = (i // 8) + 1
        ch_num = (i % 8) + 1
        sessions.append(gen_session(
            day, "キノの旅", "light_novel", "reading", duration,
            character_count=chars,
            chapter=f"{vol_num}-{ch_num}",
            volume=f"Vol. {vol_num}",
            reading_direction="vertical",
        ))

    # Natsume Yuujinchou — anime watched in this phase
    for i in range(30):
        day = 350 - i * 6 - random.randint(0, 3)
        if day < 180:
            break
        ep_count = random.choices([1, 2], weights=[8, 2])[0]
        duration = 23 * ep_count + random.randint(-2, 4)
        sessions.append(gen_session(
            day, "夏目友人帳", "anime", "listening", duration,
            episode_count=ep_count,
            episode_name=f"ep.{i + 1}" if ep_count == 1 else f"ep.{i + 1}-{i + 2}",
        ))

    # Takagi-san anime — lighter listening
    for i in range(20):
        day = 320 - i * 7 - random.randint(0, 4)
        if day < 180:
            break
        duration = random.randint(20, 28)
        sessions.append(gen_session(
            day, "からかい上手の高木さん", "anime", "listening", duration,
            episode_count=1,
            episode_name=f"ep.{i + 1}",
        ))

    # Manga: Yuru Camp
    for i in range(20):
        day = 340 - i * 8 - random.randint(0, 3)
        if day < 180:
            break
        pages = random.randint(25, 40)
        chars = pages * random.randint(120, 180)
        duration = random.randint(25, 50)
        sessions.append(gen_session(
            day, "ゆるキャン△", "manga", "reading", duration,
            page_count=pages,
            character_count=chars,
            chapter=f"ch.{i + 1}",
            volume=f"Vol. {(i // 6) + 1}",
            reading_direction="vertical",
        ))

    # YouTube study continues
    for i in range(15):
        day = random.randint(180, 360)
        ch = random.choice(["日本語の森", "Native Japanese Vlogs", "Yuyu's Japanese Tutor"])
        duration = random.randint(15, 40)
        sessions.append(gen_session(
            day, ch, "youtube", "listening", duration,
        ))


# ── Phase 3: Advanced intermediate (180-30 days ago) ──
# Daily routine. Multiple titles in rotation. ~150 sessions over 150 days.
def gen_phase3():
    # Haruhi LN — picked up after Kino. Speed ~1600-2200 chars/hr
    for i in range(35):
        day = 175 - i * 4 - random.randint(0, 2)
        if day < 30:
            break
        chars = random.randint(2500, 5000)
        chars_per_hour = 1600 + i * 15
        duration = int(chars / chars_per_hour * 60) + random.randint(-3, 6)
        duration = max(duration, 18)
        vol_num = (i // 10) + 1
        ch_num = (i % 10) + 1
        sessions.append(gen_session(
            day, "涼宮ハルヒの憂鬱", "light_novel", "reading", duration,
            character_count=chars,
            chapter=f"ch.{ch_num}",
            volume=f"Vol. {vol_num}",
            reading_direction="vertical",
        ))

    # Eupho LN — alternating with Haruhi. Slightly faster as experience builds.
    for i in range(20):
        day = 160 - i * 6 - random.randint(0, 3)
        if day < 30:
            break
        chars = random.randint(3000, 5500)
        chars_per_hour = 1800 + i * 20
        duration = int(chars / chars_per_hour * 60) + random.randint(-3, 6)
        duration = max(duration, 20)
        sessions.append(gen_session(
            day, "響け！ユーフォニアム", "light_novel", "reading", duration,
            character_count=chars,
            chapter=f"ch.{(i % 7) + 1}",
            volume=f"Vol. {(i // 7) + 1}",
            reading_direction="vertical",
        ))

    # Demon Slayer anime + manga (parallel)
    for i in range(26):
        day = 170 - i * 5 - random.randint(0, 3)
        if day < 30:
            break
        ep_count = random.choices([1, 2], weights=[7, 3])[0]
        duration = 23 * ep_count + random.randint(-2, 4)
        sessions.append(gen_session(
            day, "鬼滅の刃", "anime", "listening", duration,
            episode_count=ep_count,
            episode_name=f"ep.{i + 1}" if ep_count == 1 else f"ep.{i + 1}-{i + 2}",
        ))

    # Yuru Camp anime (after manga)
    for i in range(12):
        day = 150 - i * 7 - random.randint(0, 4)
        if day < 30:
            break
        duration = random.randint(22, 28)
        sessions.append(gen_session(
            day, "ゆるキャン△", "anime", "listening", duration,
            episode_count=1,
            episode_name=f"ep.{i + 1}",
        ))

    # CLANNAD VN — started in this phase, fully voiced so "both"
    for i in range(15):
        day = 140 - i * 8 - random.randint(0, 5)
        if day < 30:
            break
        chars = random.randint(8000, 18000)
        duration = random.randint(60, 130)
        sessions.append(gen_session(
            day, "CLANNAD", "visual_novel", "both", duration,
            character_count=chars,
            reading_direction="horizontal",
        ))

    # Bakemonogatari manga — harder
    for i in range(15):
        day = 130 - i * 9 - random.randint(0, 4)
        if day < 30:
            break
        pages = random.randint(20, 35)
        chars = pages * random.randint(150, 220)
        duration = random.randint(35, 65)
        sessions.append(gen_session(
            day, "化物語", "manga", "reading", duration,
            page_count=pages,
            character_count=chars,
            chapter=f"ch.{i + 1}",
            reading_direction="vertical",
        ))

    # Persona 4 — recent game
    for i in range(12):
        day = 100 - i * 6 - random.randint(0, 4)
        if day < 30:
            break
        chars = random.randint(5000, 12000)
        duration = random.randint(50, 120)
        sessions.append(gen_session(
            day, "ペルソナ4 ゴールデン", "game", "both", duration,
            character_count=chars,
            reading_direction="horizontal",
        ))

    # YouTube — daily-ish
    for i in range(25):
        day = random.randint(30, 180)
        ch = random.choices(
            ["日本語の森", "Native Japanese Vlogs"],
            weights=[3, 7]
        )[0]
        duration = random.randint(15, 45)
        sessions.append(gen_session(
            day, ch, "youtube", "listening", duration,
        ))


# ── Phase 4: Current month (30-1 days ago) ──
# Heavy daily activity. ~30 sessions.
def gen_phase4():
    # Lycoris Recoil anime
    for i in range(8):
        day = 28 - i * 3 - random.randint(0, 1)
        if day < 1:
            break
        ep_count = random.choices([1, 2], weights=[6, 4])[0]
        duration = 24 * ep_count + random.randint(-2, 3)
        sessions.append(gen_session(
            day, "リコリス・リコイル", "anime", "listening", duration,
            episode_count=ep_count,
            episode_name=f"ep.{i + 1}" if ep_count == 1 else f"ep.{i + 1}-{i + 2}",
        ))

    # No Game No Life LN — current main read. Speed ~2200-2700 chars/hr
    for i in range(10):
        day = 25 - i * 2 - random.randint(0, 1)
        if day < 1:
            break
        chars = random.randint(3500, 6000)
        chars_per_hour = 2200 + i * 20
        duration = int(chars / chars_per_hour * 60) + random.randint(-3, 6)
        duration = max(duration, 18)
        sessions.append(gen_session(
            day, "ノーゲーム・ノーライフ", "light_novel", "reading", duration,
            character_count=chars,
            chapter=f"ch.{i + 1}",
            volume="Vol. 1",
            reading_direction="vertical",
        ))

    # Yakuya no Hitorigoto — current anime
    for i in range(6):
        day = 20 - i * 3 - random.randint(0, 1)
        if day < 1:
            break
        duration = random.randint(22, 26)
        sessions.append(gen_session(
            day, "薬屋のひとりごと", "anime", "listening", duration,
            episode_count=1,
            episode_name=f"ep.{i + 1}",
        ))

    # YouTube viewing
    for i in range(8):
        day = random.randint(1, 29)
        duration = random.randint(15, 40)
        sessions.append(gen_session(
            day, "Native Japanese Vlogs", "youtube", "listening", duration,
        ))

    # Audiobook listening — recent addition
    for i in range(4):
        day = random.randint(2, 25)
        duration = random.randint(30, 70)
        sessions.append(gen_session(
            day, "コンビニ人間 (Audiobook)", "audiobook", "listening", duration,
            chapter=f"ch.{i + 1}",
        ))


# ── Today + this week ──
def gen_today_and_week():
    # Today: 2 sessions to make daily summary look good
    sessions.append(gen_session(
        0, "ノーゲーム・ノーライフ", "light_novel", "reading", 45,
        character_count=4800,
        chapter="ch.11",
        volume="Vol. 1",
        reading_direction="vertical",
        notes="Morning reading session — comprehension was smooth today.",
    ))
    sessions.append(gen_session(
        0, "薬屋のひとりごと", "anime", "listening", 24,
        episode_count=1,
        episode_name="ep.7",
    ))

    # Yesterday
    sessions.append(gen_session(
        1, "ノーゲーム・ノーライフ", "light_novel", "reading", 38,
        character_count=3900,
        chapter="ch.10",
        volume="Vol. 1",
        reading_direction="vertical",
    ))
    sessions.append(gen_session(
        1, "Native Japanese Vlogs", "youtube", "listening", 22,
    ))

    # Earlier this week
    for d in [2, 3, 4, 5, 6]:
        if random.random() > 0.2:
            sessions.append(gen_session(
                d, "ノーゲーム・ノーライフ", "light_novel", "reading",
                random.randint(25, 55),
                character_count=random.randint(2800, 5500),
                chapter=f"ch.{10 - d}",
                volume="Vol. 1",
                reading_direction="vertical",
            ))
        if random.random() > 0.4:
            sessions.append(gen_session(
                d, "リコリス・リコイル", "anime", "listening",
                random.randint(22, 28),
                episode_count=1,
                episode_name=f"ep.{8 - d}",
            ))


gen_phase1()
gen_phase2()
gen_phase3()
gen_phase4()
gen_today_and_week()


# ────────────────────────────────────────────
#  STUDY SESSIONS
# ────────────────────────────────────────────
# Anki review nearly daily, plus textbook chapters periodically.

study_sessions = []

# Daily-ish Anki reviews for the full timeline
for day in range(540, 0, -1):
    # ~85% chance per day
    if random.random() < 0.85:
        deck = random.choice([
            "Anki — Core 2k/6k", "Anki — Kaishi 1.5k", "Anki — Mining Deck (personal)"
        ])
        # Newer days = mining deck more likely
        if day < 200:
            deck = random.choices(
                ["Anki — Core 2k/6k", "Anki — Mining Deck (personal)"],
                weights=[2, 8]
            )[0]
        elif day < 400:
            deck = random.choices(
                ["Anki — Core 2k/6k", "Anki — Kaishi 1.5k", "Anki — Mining Deck (personal)"],
                weights=[5, 3, 2]
            )[0]

        reviews = random.randint(80, 180)
        new_cards = random.choice([0, 0, 5, 10, 10, 15, 20])
        duration = max(8, reviews // 8 + random.randint(-3, 5))
        study_sessions.append({
            "days_ago": day,
            "study_type": "anki",
            "duration_minutes": duration,
            "resource_name": deck,
            "anki_deck": deck.replace("Anki — ", ""),
            "anki_reviews": reviews,
            "anki_new_cards": new_cards,
            "topic_area": "vocab",
        })

# Today's Anki review
study_sessions.append({
    "days_ago": 0,
    "study_type": "anki",
    "duration_minutes": 18,
    "resource_name": "Anki — Mining Deck (personal)",
    "anki_deck": "Mining Deck (personal)",
    "anki_reviews": 142,
    "anki_new_cards": 10,
    "topic_area": "vocab",
})

# Genki textbook sessions (early)
for i in range(20):
    day = 530 - i * 8 - random.randint(0, 4)
    if day < 340:
        break
    study_sessions.append({
        "days_ago": day,
        "study_type": "textbook",
        "duration_minutes": random.randint(30, 60),
        "resource_name": "Genki II",
        "topic_area": random.choice(["grammar", "vocab", "kanji"]),
    })

# Tobira sessions (later)
for i in range(15):
    day = 200 - i * 9 - random.randint(0, 4)
    if day < 10:
        break
    study_sessions.append({
        "days_ago": day,
        "study_type": "textbook",
        "duration_minutes": random.randint(40, 80),
        "resource_name": "Tobira",
        "topic_area": random.choice(["grammar", "reading_comp", "vocab"]),
    })

# Bunpro sessions sprinkled in
for i in range(40):
    day = random.randint(30, 400)
    study_sessions.append({
        "days_ago": day,
        "study_type": "grammar",
        "duration_minutes": random.randint(8, 20),
        "resource_name": "Bunpro",
        "topic_area": "grammar",
    })


# ────────────────────────────────────────────
#  EXAM SCORES (JLPT mocks)
# ────────────────────────────────────────────

exam_scores = [
    {
        "days_ago": 420,
        "level": "N5",
        "exam_type": "mock",
        "resource_name": "日本語の森 N4 Mock",  # using N4 mock at N5 level early
        "source_text": "日本語の森 N5 Mock #1",
        "sections": {
            "文字・語彙": {"sections": {
                "漢字読み": {"score": 6, "total": 8},
                "表記":     {"score": 5, "total": 6},
                "文脈規定": {"score": 6, "total": 10},
                "言い換え類義": {"score": 3, "total": 5},
            }},
            "文法・読解": {"sections": {
                "文法形式の判断": {"score": 9, "total": 15},
                "文の組み立て":   {"score": 3, "total": 5},
                "文章の文法":     {"score": 3, "total": 5},
                "内容理解(短文)": {"score": 2, "total": 3},
            }},
            "聴解": {"sections": {
                "課題理解":   {"score": 5, "total": 8},
                "ポイント理解": {"score": 4, "total": 7},
                "発話表現":   {"score": 3, "total": 5},
            }},
        },
        "notes": "First mock. Listening was rough but vocab section went well.",
    },
    {
        "days_ago": 270,
        "level": "N4",
        "exam_type": "mock",
        "resource_name": "日本語の森 N4 Mock",
        "source_text": "日本語の森 N4 Mock #1",
        "sections": {
            "文字・語彙": {"sections": {
                "漢字読み":   {"score": 7, "total": 8},
                "表記":       {"score": 6, "total": 6},
                "文脈規定":   {"score": 9, "total": 10},
                "言い換え類義": {"score": 4, "total": 5},
            }},
            "文法・読解": {"sections": {
                "文法形式の判断": {"score": 12, "total": 15},
                "文の組み立て":   {"score": 4, "total": 5},
                "文章の文法":     {"score": 4, "total": 5},
                "内容理解(短文)": {"score": 3, "total": 3},
            }},
            "聴解": {"sections": {
                "課題理解":   {"score": 7, "total": 8},
                "ポイント理解": {"score": 5, "total": 7},
                "発話表現":   {"score": 4, "total": 5},
            }},
        },
        "notes": "Solid N4 pass. Ready to start prepping for N3.",
    },
    {
        "days_ago": 90,
        "level": "N3",
        "exam_type": "mock",
        "resource_name": "日本語の森 N3 Mock",
        "source_text": "日本語の森 N3 Mock #1",
        "sections": {
            "文字・語彙": {"sections": {
                "漢字読み":   {"score": 5, "total": 8},
                "表記":       {"score": 4, "total": 6},
                "文脈規定":   {"score": 7, "total": 11},
                "言い換え類義": {"score": 3, "total": 5},
                "用法":       {"score": 3, "total": 5},
            }},
            "文法・読解": {"sections": {
                "文法形式の判断": {"score": 9, "total": 13},
                "文の組み立て":   {"score": 3, "total": 5},
                "文章の文法":     {"score": 3, "total": 5},
                "内容理解(短文)": {"score": 3, "total": 4},
                "内容理解(中文)": {"score": 4, "total": 6},
            }},
            "聴解": {"sections": {
                "課題理解":   {"score": 4, "total": 6},
                "ポイント理解": {"score": 4, "total": 6},
                "概要理解":   {"score": 2, "total": 3},
                "発話表現":   {"score": 3, "total": 4},
            }},
        },
        "notes": "First N3 attempt. Vocab is the weakest area — need more reading.",
    },
    {
        "days_ago": 20,
        "level": "N3",
        "exam_type": "mock",
        "resource_name": "日本語の森 N3 Mock",
        "source_text": "日本語の森 N3 Mock #2",
        "sections": {
            "文字・語彙": {"sections": {
                "漢字読み":   {"score": 7, "total": 8},
                "表記":       {"score": 5, "total": 6},
                "文脈規定":   {"score": 9, "total": 11},
                "言い換え類義": {"score": 4, "total": 5},
                "用法":       {"score": 4, "total": 5},
            }},
            "文法・読解": {"sections": {
                "文法形式の判断": {"score": 11, "total": 13},
                "文の組み立て":   {"score": 4, "total": 5},
                "文章の文法":     {"score": 4, "total": 5},
                "内容理解(短文)": {"score": 4, "total": 4},
                "内容理解(中文)": {"score": 5, "total": 6},
            }},
            "聴解": {"sections": {
                "課題理解":   {"score": 5, "total": 6},
                "ポイント理解": {"score": 5, "total": 6},
                "概要理解":   {"score": 3, "total": 3},
                "発話表現":   {"score": 4, "total": 4},
            }},
        },
        "notes": "Huge improvement across all sections. Confident for the official N3 exam.",
    },
]


# ────────────────────────────────────────────
#  GOALS
# ────────────────────────────────────────────

goals = [
    {
        "name": "Daily reading",
        "goal_type": "recurring",
        "metric": "character_count",
        "target_value": 5000,
        "period": "daily",
        "activity_type": "reading",
        "health_window_days": 60,
        "is_active": 1,
        "created_days_ago": 300,
    },
    {
        "name": "Daily listening",
        "goal_type": "recurring",
        "metric": "duration_minutes",
        "target_value": 30,
        "period": "daily",
        "activity_type": "listening",
        "health_window_days": 60,
        "is_active": 1,
        "created_days_ago": 300,
    },
    {
        "name": "Weekly immersion",
        "goal_type": "recurring",
        "metric": "duration_minutes",
        "target_value": 600,  # 10 hours/week
        "period": "weekly",
        "health_window_days": 84,
        "is_active": 1,
        "created_days_ago": 200,
    },
    {
        "name": "Read 1 million characters",
        "goal_type": "lifetime",
        "metric": "character_count",
        "target_value": 1_000_000,
        "is_active": 1,
        "created_days_ago": 400,
    },
    {
        "name": "Reach 300 hours of immersion",
        "goal_type": "lifetime",
        "metric": "duration_minutes",
        "target_value": 18_000,  # 300 hr in minutes
        "is_active": 0,
        "achieved_days_ago": 60,
        "created_days_ago": 500,
    },
    {
        "name": "Reach 100 hours of immersion",
        "goal_type": "lifetime",
        "metric": "duration_minutes",
        "target_value": 6_000,
        "is_active": 0,
        "achieved_days_ago": 380,
        "created_days_ago": 530,
    },
]


# ────────────────────────────────────────────
#  MILESTONES
# ────────────────────────────────────────────

milestones = [
    {
        "title": "First manga finished: よつばと！ Vol. 1",
        "days_ago": 450,
        "metric": "page_count",
        "metric_value": 224,
        "notes": "First manga read entirely in Japanese. Took 3 months.",
    },
    {
        "title": "Passed N5 mock exam",
        "days_ago": 420,
        "notes": "Got 64% overall on first mock. Listening still weak.",
    },
    {
        "title": "Reached 100 hours of immersion",
        "days_ago": 380,
        "metric": "duration_minutes",
        "metric_value": 6000,
        "filter": {},
    },
    {
        "title": "First light novel started: キノの旅",
        "days_ago": 340,
        "notes": "Slow going at first — looking up many words per page.",
    },
    {
        "title": "Finished カードキャプターさくら (70 episodes)",
        "days_ago": 380,
        "metric": "episode_count",
        "metric_value": 70,
        "filter": {"title_text": "カードキャプターさくら"},
    },
    {
        "title": "Passed N4 mock exam",
        "days_ago": 270,
        "notes": "Solid 80%+ across all sections.",
    },
    {
        "title": "First LN volume finished: キノの旅 Vol. 1",
        "days_ago": 240,
        "metric": "character_count",
        "metric_value": 65000,
        "filter": {"title_text": "キノの旅", "medium_type": "light_novel"},
    },
    {
        "title": "Started reading vertical text comfortably",
        "days_ago": 220,
    },
    {
        "title": "Finished CLANNAD common route",
        "days_ago": 80,
        "notes": "First major VN milestone. Heavy on listening practice.",
    },
    {
        "title": "Reached 300 hours of immersion",
        "days_ago": 60,
        "metric": "duration_minutes",
        "metric_value": 18000,
    },
    {
        "title": "N3 mock exam: huge improvement",
        "days_ago": 20,
        "notes": "Jumped from 60% to 87% between attempts.",
    },
]


# ────────────────────────────────────────────
#  WRITE OUT
# ────────────────────────────────────────────

# Sort sessions by days_ago descending (oldest first → makes the JSON readable)
sessions.sort(key=lambda s: -s["days_ago"])
study_sessions.sort(key=lambda s: -s["days_ago"])

output = {
    "_meta": {
        "description": "Demo data for the Japanese immersion tracker. "
                       "Dates are specified as days_ago offsets — the migration "
                       "script converts these to actual dates so re-running "
                       "always produces 'current' data.",
        "session_count": len(sessions),
        "study_session_count": len(study_sessions),
        "title_count": len(TITLES),
    },
    "titles": TITLES,
    "resources": RESOURCES,
    "immersion_sessions": sessions,
    "study_sessions": study_sessions,
    "exam_scores": exam_scores,
    "goals": goals,
    "milestones": milestones,
}

with open("/home/claude/demo/demo.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Generated demo.json:")
print(f"  Titles:            {len(TITLES)}")
print(f"  Resources:         {len(RESOURCES)}")
print(f"  Immersion sessions: {len(sessions)}")
print(f"  Study sessions:    {len(study_sessions)}")
print(f"  Exam scores:       {len(exam_scores)}")
print(f"  Goals:             {len(goals)}")
print(f"  Milestones:        {len(milestones)}")

# Summary by medium
from collections import Counter
medium_count = Counter(s["medium_type"] for s in sessions)
print("\n  Sessions by medium:")
for m, c in medium_count.most_common():
    print(f"    {m:15s} {c}")

# Total reading vs listening duration
read_dur = sum(s["duration_minutes"] for s in sessions
               if s["activity_type"] == "reading")
listen_dur = sum(s["duration_minutes"] for s in sessions
                 if s["activity_type"] == "listening")
both_dur = sum(s["duration_minutes"] for s in sessions
               if s["activity_type"] == "both")
total_min = read_dur + listen_dur + both_dur
print(f"\n  Total time: {total_min} min ({total_min/60:.1f} hours)")
print(f"  Reading:   {read_dur} min")
print(f"  Listening: {listen_dur} min")
print(f"  Both:      {both_dur} min")

# Char count check
total_chars = sum(s.get("character_count", 0) or 0 for s in sessions)
print(f"  Total characters: {total_chars:,}")
