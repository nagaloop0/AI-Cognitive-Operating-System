"""
Tests for the "when to speak" rules and the tracker loop (ActivityDriver), with fake time and no macOS APIs.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from backend.driver import ActivityDriver
from backend.models import AppActivity, AssistantMessage, UserPreference
from backend.settings import AssistantSettings
from backend.timing import idle_threshold_seconds, is_end_of_day_due, is_passive, is_welcome_back
from backend.timeutil import local_tz

SETTINGS = AssistantSettings()  # summary 19:00, latest 23:35, break 5 min, away 15 min, idle 120 s


def local(hhmm: str) -> datetime:
    hours, minutes = map(int, hhmm.split(":"))
    return datetime(2026, 10, 5, hours, minutes, tzinfo=local_tz())


# ---- rules ----------------------------------------------------------------------------------------

def test_end_of_day_waits_until_summary_time():
    assert not is_end_of_day_due(local("18:59"), 600, SETTINGS, already_sent_today=False)


def test_end_of_day_waits_while_you_are_typing():
    assert not is_end_of_day_due(local("19:30"), 10, SETTINGS, already_sent_today=False)


def test_end_of_day_comes_at_the_next_break():
    assert is_end_of_day_due(local("19:30"), 5 * 60, SETTINGS, already_sent_today=False)


def test_end_of_day_comes_at_the_latest_time_even_while_working():
    assert is_end_of_day_due(local("23:35"), 0, SETTINGS, already_sent_today=False)


def test_end_of_day_only_once_per_day():
    assert not is_end_of_day_due(local("23:50"), 600, SETTINGS, already_sent_today=True)


def test_thinking_pause_is_not_a_welcome_back():
    assert not is_welcome_back(10, SETTINGS)
    assert is_welcome_back(25 * 60, SETTINGS)


def test_videos_and_calls_get_a_long_idle_limit():
    assert is_passive("Google Chrome", "Lo-fi beats - YouTube")
    assert is_passive("zoom.us", "Zoom Meeting")
    assert idle_threshold_seconds("Code", "main.py", SETTINGS) == 120
    assert idle_threshold_seconds("Google Chrome", "Lo-fi beats - YouTube", SETTINGS) == 30 * 60


# ---- driver ---------------------------------------------------------------------------------------

T0 = datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc)


def make_driver(db):
    factory = sessionmaker(bind=db.get_bind())
    return ActivityDriver(session_factory=factory, run_in_background=False)


def test_window_change_closes_the_old_record_and_opens_a_new_one(db):
    driver = make_driver(db)

    driver.tick(T0, ("Code", "main.py"), keys=5, clicks=0)
    driver.tick(T0 + timedelta(seconds=60), ("Google Chrome", "Docs"), keys=1, clicks=1)

    rows = db.query(AppActivity).order_by(AppActivity.id).all()
    assert [(r.app_name, r.duration_seconds) for r in rows] == [("Code", 60), ("Google Chrome", 0)]


def test_private_app_title_is_not_stored(db):
    make_driver(db).tick(T0, ("WhatsApp", "Chat with Mum"), keys=1, clicks=0)

    assert db.query(AppActivity).one().window_title == "(private)"


def test_idle_closes_the_record_at_the_last_input(db):
    driver = make_driver(db)
    driver.tick(T0, ("Code", "main.py"), keys=3, clicks=0)
    driver.tick(T0 + timedelta(seconds=10), ("Code", "main.py"), keys=1, clicks=0)

    driver.tick(T0 + timedelta(seconds=200), ("Code", "main.py"), keys=0, clicks=0)

    record = db.query(AppActivity).one()
    assert driver.is_idle
    assert record.duration_seconds == 10


def test_return_after_a_long_absence_leaves_a_welcome_back_message(db):
    driver = make_driver(db)
    driver.tick(T0, ("Code", "digest.py — explore_p"), keys=3, clicks=0)
    driver.tick(T0 + timedelta(minutes=10), ("Code", "digest.py — explore_p"), keys=2, clicks=0)
    driver.tick(T0 + timedelta(minutes=13), ("Code", "digest.py — explore_p"), keys=0, clicks=0)  # idle

    driver.tick(T0 + timedelta(minutes=40), ("Code", "digest.py — explore_p"), keys=4, clicks=0)

    message = db.query(AssistantMessage).one()
    assert message.kind == "welcome_back"
    assert "away for 30 min" in message.body
    assert "digest.py — explore_p" in message.body


def test_short_absence_leaves_no_message(db):
    driver = make_driver(db)
    driver.tick(T0, ("Code", "a.py"), keys=1, clicks=0)
    driver.tick(T0 + timedelta(minutes=3), ("Code", "a.py"), keys=0, clicks=0)  # idle after 2 min

    driver.tick(T0 + timedelta(minutes=5), ("Code", "a.py"), keys=1, clicks=0)

    assert db.query(AssistantMessage).count() == 0


def test_paused_tracking_records_nothing(db):
    db.add(UserPreference(key="is_tracking_paused", value="true"))
    db.commit()

    make_driver(db).tick(T0, ("Code", "a.py"), keys=1, clicks=0)

    assert db.query(AppActivity).count() == 0
