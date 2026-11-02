"""
Tests for the day digest. Each expected number is worked out by hand in the comments.
The digest runs in UTC here, so `at("2026-10-05", "09:00")` is 09:00 of that day.
"""
from datetime import date, timezone

from backend.digest import build_day_digest
from backend.models import TitleCategory
from conftest import add_activity, at

DAY = date(2026, 10, 5)
UTC = timezone.utc
PRIVATE = ["WhatsApp"]


def digest(db):
    return build_day_digest(db, DAY, PRIVATE, tz=UTC)


def test_empty_day(db):
    result = digest(db)

    assert result.is_empty
    assert "No activity recorded" in result.to_prompt_text()


def test_minutes_breaks_switches_and_focus(db):
    # 09:00-10:00 Code, 10:00-10:20 Chrome, (break 10:20-10:50), 10:50-11:30 Code
    add_activity(db, "Code", "digest.py — explore_p", at("2026-10-05", "09:00"), 60)
    add_activity(db, "Google Chrome", "pgvector docs", at("2026-10-05", "10:00"), 20)
    add_activity(db, "Code", "summary.py — explore_p", at("2026-10-05", "10:50"), 40)

    result = digest(db)

    assert result.active_minutes == 120            # 60 + 20 + 40
    assert result.break_minutes == 30              # 10:20 -> 10:50
    assert result.app_switches == 1                # Code -> Chrome; Chrome -> Code is after a 30 min gap
    assert [(a.app_name, a.minutes) for a in result.apps] == [("Code", 100), ("Google Chrome", 20)]
    assert result.longest_focus.app_name == "Code" and result.longest_focus.minutes == 60
    assert result.first_activity.hour == 9 and result.last_activity.hour == 11


def test_top_titles_are_ranked_by_time_and_redacted(db):
    add_activity(db, "Google Chrome", "Inbox - me@mail.com", at("2026-10-05", "09:00"), 5)
    add_activity(db, "Google Chrome", "FastAPI docs", at("2026-10-05", "09:05"), 25)

    chrome = digest(db).apps[0]

    assert chrome.top_titles == ["FastAPI docs", "Inbox - [email]"]


def test_private_apps_are_grouped_without_titles(db):
    add_activity(db, "WhatsApp", "Chat with Mum", at("2026-10-05", "09:00"), 12)

    result = digest(db)

    assert [(a.app_name, a.minutes, a.top_titles) for a in result.apps] == [("Private apps", 12, [])]
    assert "Mum" not in result.to_prompt_text()


def test_work_past_midnight_is_split_between_days(db):
    # 23:30 on Oct 4 until 00:30 on Oct 5: only the 30 minutes after midnight belong to Oct 5
    add_activity(db, "Code", "late.py", at("2026-10-04", "23:30"), 60)

    assert digest(db).active_minutes == 30


def test_short_interruption_does_not_break_focus(db):
    # Code 30 min, 1 min gap, Code 30 min -> one 60 min focus block
    add_activity(db, "Code", "a.py", at("2026-10-05", "09:00"), 30)
    add_activity(db, "Code", "b.py", at("2026-10-05", "09:31"), 30)

    assert digest(db).longest_focus.minutes == 60


def test_category_minutes_use_known_labels(db):
    add_activity(db, "Code", "a.py", at("2026-10-05", "09:00"), 50)
    add_activity(db, "Google Chrome", "YouTube - music", at("2026-10-05", "09:50"), 10)
    db.add_all([
        TitleCategory(app_name="Code", window_title="a.py", category="work", source="rule"),
        TitleCategory(app_name="Google Chrome", window_title="YouTube - music", category="fun", source="llm"),
    ])
    db.commit()

    assert digest(db).category_minutes == {"work": 50, "fun": 10}


def test_prompt_text_contains_the_key_facts(db):
    add_activity(db, "Code", "digest.py — explore_p", at("2026-10-05", "09:00"), 90)

    text = digest(db).to_prompt_text()

    assert "Monday 2026-10-05" in text
    assert "Active time: 1 h 30 min" in text
    assert "- Code: 90 min | digest.py — explore_p" in text
