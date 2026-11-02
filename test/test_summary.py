"""
Tests for the AI daily summary with a fake model (no Ollama needed).
"""
from datetime import date, timedelta, timezone

import pytest

from backend.digest import build_day_digest
from backend.llm_client import LLMResponseError, LLMUnavailableError
from backend.models import DailySummary
from backend.summary import generate_summary, get_daily_summary
from backend.timeutil import local_day_bounds, local_today
from conftest import FakeLLM, add_activity, at

DAY = date(2026, 10, 5)
GOOD_ANSWER = {
    "headline": "Deep work on the digest",
    "focus_areas": ["digest.py", "pgvector docs"],
    "insight": "Your morning was focused.",
    "suggestion": "Start with the summary module tomorrow.",
}


def a_day(db):
    add_activity(db, "Code", "digest.py — explore_p", at("2026-10-05", "09:00"), 90)
    add_activity(db, "Google Chrome", "pgvector docs", at("2026-10-05", "10:30"), 30)
    return build_day_digest(db, DAY, [], tz=timezone.utc)


def test_valid_answer_is_used_and_numbers_come_from_the_digest(db):
    llm = FakeLLM(GOOD_ANSWER)

    result = generate_summary(a_day(db), llm)

    assert result.source == "llm" and result.attempts == 1
    assert result.headline == "Deep work on the digest"
    assert [(t.app_name, t.minutes) for t in result.time_split] == [("Code", 90), ("Google Chrome", 30)]


def test_prompt_contains_the_report_and_a_json_schema(db):
    llm = FakeLLM(GOOD_ANSWER)

    generate_summary(a_day(db), llm, tone="strict")

    call = llm.calls[0]
    assert "digest.py — explore_p" in call["messages"][1]["content"]
    assert "focused coach" in call["messages"][0]["content"]
    assert set(call["json_schema"]["properties"]) == {"headline", "focus_areas", "insight", "suggestion"}


def test_invalid_answer_is_retried_once_with_the_error_explained(db):
    llm = FakeLLM({"headline": "Only a headline"}, GOOD_ANSWER)

    result = generate_summary(a_day(db), llm)

    assert result.source == "llm" and result.attempts == 2
    assert "invalid" in llm.calls[1]["messages"][-1]["content"]


def test_two_invalid_answers_give_the_fallback(db):
    llm = FakeLLM(LLMResponseError("not JSON"), {"headline": "x"})

    result = generate_summary(a_day(db), llm)

    assert result.source == "fallback"
    assert "invalid twice" in result.notice


def test_model_down_gives_the_fallback_immediately(db):
    llm = FakeLLM(LLMUnavailableError("Ollama is not running"))

    result = generate_summary(a_day(db), llm)

    assert result.source == "fallback" and len(llm.calls) == 1
    assert result.headline == "2 h active, mostly in Code"
    assert "AI not available" in result.notice


def test_empty_day_does_not_call_the_model(db):
    llm = FakeLLM()

    result = generate_summary(build_day_digest(db, DAY, [], tz=timezone.utc), llm)

    assert result.source == "fallback" and llm.calls == []


def yesterday_with_activity(db):
    day = local_today() - timedelta(days=1)
    start, _ = local_day_bounds(day)
    add_activity(db, "Code", "digest.py", start + timedelta(hours=9), 60)
    return day


def test_finished_day_is_cached(db):
    day = yesterday_with_activity(db)
    # Code is labelled by a rule, so the only model call is the summary itself
    llm = FakeLLM(GOOD_ANSWER)

    first = get_daily_summary(db, day, llm)
    second = get_daily_summary(db, day, llm)

    assert first.headline == second.headline == "Deep work on the digest"
    assert len(llm.calls) == 1
    assert db.query(DailySummary).count() == 1


def test_refresh_makes_a_new_summary(db):
    day = yesterday_with_activity(db)
    llm = FakeLLM(GOOD_ANSWER, GOOD_ANSWER | {"headline": "Second version"})

    get_daily_summary(db, day, llm)
    refreshed = get_daily_summary(db, day, llm, refresh=True)

    assert refreshed.headline == "Second version"
    assert db.query(DailySummary).count() == 1


def test_fallback_is_not_cached_so_the_model_is_tried_again(db):
    day = yesterday_with_activity(db)
    llm = FakeLLM(LLMUnavailableError("down"), GOOD_ANSWER)

    assert get_daily_summary(db, day, llm).source == "fallback"
    assert get_daily_summary(db, day, llm).source == "llm"


def test_future_day_is_rejected(db):
    with pytest.raises(ValueError):
        get_daily_summary(db, local_today() + timedelta(days=1), FakeLLM())
