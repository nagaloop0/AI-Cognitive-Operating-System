"""
Unit tests for the Markov pattern engine.
Uses a throwaway in-memory SQLite database, so the real PostgreSQL data is never touched
and no notification is sent.
Run: venv/bin/python -m pytest test/test_pattern_engine.py -v
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import Base
from backend.models import AppActivity, HabitPattern
from backend.pattern_engine import MarkovPatternEngine  

START = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def add_sequence(db, apps, minutes_each=1, gap_minutes=0, start=START):
    """Insert one activity per app, back to back (optionally with a gap between them)."""
    t = start
    for app in apps:
        end = t + timedelta(minutes=minutes_each)
        db.add(AppActivity(app_name=app, window_title=app, start_time=t, end_time=end))
        t = end + timedelta(minutes=gap_minutes)
    db.commit()


def as_dict(patterns):
    return {(p["trigger"], p["predicted"]): p for p in patterns}


def test_learns_conditional_probability(db):
    # From Chrome: 2x to Code, 1x to Slack -> P(Code | Chrome) = 2/3
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code", "Chrome", "Slack"])

    learned = as_dict(MarkovPatternEngine.train_patterns(db))

    assert learned[("Chrome", "Code")]["count"] == 2
    assert learned[("Chrome", "Code")]["confidence"] == pytest.approx(0.667)
    assert learned[("Code", "Chrome")]["confidence"] == 1.0


def test_one_off_transition_is_filtered_as_noise(db):
    # Chrome -> Slack happened only once: below MIN_OCCURRENCES (2)
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code", "Chrome", "Slack"])

    learned = as_dict(MarkovPatternEngine.train_patterns(db))

    assert ("Chrome", "Slack") not in learned


def test_low_confidence_is_filtered(db):
    # From A: B, C, D twice each -> each 2/6 = 0.333, below the 0.50 threshold
    add_sequence(db, ["A", "B", "A", "C", "A", "D", "A", "B", "A", "C", "A", "D"])

    learned = as_dict(MarkovPatternEngine.train_patterns(db))

    assert not any(trigger == "A" for trigger, _ in learned)


def test_long_idle_gap_breaks_the_chain(db):
    # 10 minutes between apps is more than MAX_SESSION_GAP_SECONDS (5 min): not one workflow
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code"], gap_minutes=10)

    assert MarkovPatternEngine.train_patterns(db) == []


def test_same_app_twice_is_not_a_switch(db):
    # Code -> Code (new window in the same app) must not count as a transition
    add_sequence(db, ["Code", "Code", "Chrome", "Code", "Code", "Chrome"])

    learned = as_dict(MarkovPatternEngine.train_patterns(db))

    assert ("Code", "Code") not in learned
    assert learned[("Code", "Chrome")]["count"] == 2


def test_retraining_updates_instead_of_duplicating(db):
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code"])
    MarkovPatternEngine.train_patterns(db)
    MarkovPatternEngine.train_patterns(db)

    rows = db.query(HabitPattern).filter_by(trigger_sequence="Chrome", predicted_action="Code").all()

    assert len(rows) == 1


def test_habit_that_drops_below_threshold_is_removed(db):
    # Monday: Chrome -> Code twice, a habit at 100%
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code"])
    MarkovPatternEngine.train_patterns(db)
    assert db.query(HabitPattern).filter_by(trigger_sequence="Chrome", predicted_action="Code").count() == 1

    # Later: Chrome -> Slack three times, so Chrome -> Code falls to 2/5 = 40%
    add_sequence(db, ["Chrome", "Slack", "Chrome", "Slack", "Chrome", "Slack"], start=START + timedelta(hours=2))
    MarkovPatternEngine.train_patterns(db)

    assert db.query(HabitPattern).filter_by(trigger_sequence="Chrome", predicted_action="Code").count() == 0
    assert MarkovPatternEngine.predict_next("Chrome", db)["predicted_app"] == "Slack"


def test_predict_next_returns_best_pattern(db):
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code", "Chrome", "Slack"])
    MarkovPatternEngine.train_patterns(db)

    pred = MarkovPatternEngine.predict_next("Chrome", db)

    assert pred["predicted_app"] == "Code"
    assert pred["confidence_percent"] == 66


def test_predict_next_unknown_app_returns_none(db):
    add_sequence(db, ["Chrome", "Code", "Chrome", "Code"])
    MarkovPatternEngine.train_patterns(db)

    assert MarkovPatternEngine.predict_next("Spotify", db) is None
    assert MarkovPatternEngine.predict_next("", db) is None


def test_needs_at_least_two_activities(db):
    add_sequence(db, ["Chrome"])

    assert MarkovPatternEngine.train_patterns(db) == []
