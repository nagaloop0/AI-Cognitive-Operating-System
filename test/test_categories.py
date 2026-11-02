"""
Tests for title categories: rules, model batches, user corrections.
"""
from datetime import timedelta

import pytest

from backend.categories import categorize_day, category_of, set_category
from backend.llm_client import LLMResponseError
from backend.models import TitleCategory
from backend.timeutil import local_day_bounds, local_today
from conftest import FakeLLM, add_activity

DAY = local_today() - timedelta(days=1)


def add(db, app, title, hour):
    start, _ = local_day_bounds(DAY)
    add_activity(db, app, title, start + timedelta(hours=hour), 10)


def test_clear_apps_use_rules_without_the_model(db):
    add(db, "Slack", "general", 9)
    add(db, "Code", "main.py", 10)
    llm = FakeLLM()

    assert categorize_day(db, DAY, llm) == 2
    assert llm.calls == []
    assert category_of(db, "Slack", "general") == "communication"
    assert category_of(db, "Code", "main.py") == "work"


def test_browser_titles_are_labelled_by_the_model(db):
    add(db, "Google Chrome", "Python tutorial for beginners - YouTube", 9)
    add(db, "Google Chrome", "Funny cats - YouTube", 10)
    # Titles are sent sorted: index 0 = "Funny cats", index 1 = "Python tutorial"
    llm = FakeLLM({"labels": [{"index": 0, "category": "fun"}, {"index": 1, "category": "learning"}]})

    categorize_day(db, DAY, llm)

    assert category_of(db, "Google Chrome", "Python tutorial for beginners - YouTube") == "learning"
    assert category_of(db, "Google Chrome", "Funny cats - YouTube") == "fun"


def test_titles_are_labelled_only_once(db):
    add(db, "Google Chrome", "News", 9)
    llm = FakeLLM({"labels": [{"index": 0, "category": "fun"}]})

    categorize_day(db, DAY, llm)
    categorize_day(db, DAY, llm)

    assert len(llm.calls) == 1


def test_made_up_indexes_are_ignored(db):
    add(db, "Google Chrome", "News", 9)
    llm = FakeLLM({"labels": [{"index": 7, "category": "fun"}, {"index": 0, "category": "other"}]})

    categorize_day(db, DAY, llm)

    assert db.query(TitleCategory).count() == 1


def test_broken_model_answer_skips_the_batch_for_a_later_retry(db):
    add(db, "Google Chrome", "News", 9)

    assert categorize_day(db, DAY, FakeLLM(LLMResponseError("bad"))) == 0
    assert category_of(db, "Google Chrome", "News") is None


def test_user_correction_wins_and_is_kept(db):
    add(db, "Google Chrome", "Chess openings - YouTube", 9)
    categorize_day(db, DAY, FakeLLM({"labels": [{"index": 0, "category": "fun"}]}))

    set_category(db, "Google Chrome", "Chess openings - YouTube", "learning")

    row = db.query(TitleCategory).one()
    assert (row.category, row.source) == ("learning", "user")


def test_unknown_category_is_rejected(db):
    with pytest.raises(ValueError):
        set_category(db, "Code", "x", "sleeping")


def test_schema_requires_one_label_per_title(db):
    add(db, "Google Chrome", "News", 9)
    add(db, "Google Chrome", "Docs", 10)
    llm = FakeLLM({"labels": [{"index": 0, "category": "learning"}, {"index": 1, "category": "fun"}]})

    categorize_day(db, DAY, llm)

    labels_schema = llm.calls[0]["json_schema"]["properties"]["labels"]
    assert (labels_schema["minItems"], labels_schema["maxItems"]) == (2, 2)
