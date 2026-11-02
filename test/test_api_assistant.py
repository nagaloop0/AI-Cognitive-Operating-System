"""
API tests for summary, settings, categories and assistant messages.
The database is in-memory SQLite and the model is FakeLLM, injected through FastAPI dependency overrides.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.llm_client import LLMUnavailableError, get_llm_client
from backend.main import app
from backend.models import AppActivity, AssistantMessage, DailySummary, TitleCategory
from backend.timeutil import local_day_bounds, local_today
from conftest import FakeLLM, add_activity

YESTERDAY = local_today() - timedelta(days=1)
GOOD_ANSWER = {"headline": "Focused coding day", "focus_areas": ["digest.py"],
               "insight": "Long morning focus.", "suggestion": "Keep mornings for deep work."}


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def client(db, llm):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm
    yield TestClient(app)
    app.dependency_overrides.clear()


def add_yesterday(db, app_name="Code", title="digest.py", hour=9, minutes=60):
    start, _ = local_day_bounds(YESTERDAY)
    add_activity(db, app_name, title, start + timedelta(hours=hour), minutes)


def test_daily_summary_endpoint(client, db, llm):
    add_yesterday(db)
    llm.answers.append(GOOD_ANSWER)

    response = client.get("/api/summary/daily", params={"day": YESTERDAY.isoformat()})

    assert response.status_code == 200
    body = response.json()
    assert body["headline"] == "Focused coding day"
    assert body["source"] == "llm"
    assert body["time_split"] == [{"app_name": "Code", "minutes": 60}]
    assert db.query(DailySummary).count() == 1


def test_daily_summary_falls_back_when_model_is_down(client, db, llm):
    add_yesterday(db)
    llm.answers.append(LLMUnavailableError("down"))

    body = client.get("/api/summary/daily", params={"day": YESTERDAY.isoformat()}).json()

    assert body["source"] == "fallback"
    assert body["notice"].startswith("AI not available")


def test_future_day_is_a_bad_request(client):
    tomorrow = (local_today() + timedelta(days=1)).isoformat()

    assert client.get("/api/summary/daily", params={"day": tomorrow}).status_code == 400


def test_digest_endpoint_needs_no_model(client, db, llm):
    add_yesterday(db, minutes=45)

    body = client.get("/api/summary/digest", params={"day": YESTERDAY.isoformat()}).json()

    assert body["active_minutes"] == 45 and llm.calls == []


def test_settings_round_trip(client):
    assert client.get("/api/settings").json()["tone"] == "friendly"

    updated = client.put("/api/settings", json={"tone": "funny", "away_minutes": 25}).json()

    assert (updated["tone"], updated["away_minutes"]) == ("funny", 25)
    assert client.get("/api/settings").json()["tone"] == "funny"


def test_invalid_settings_are_rejected(client):
    assert client.put("/api/settings", json={"summary_time": "25:99"}).status_code == 422
    assert client.put("/api/settings", json={"unknown": 1}).status_code == 422


def test_categories_for_a_day_and_user_correction(client, db):
    add_yesterday(db, "Slack", "general", hour=9, minutes=20)
    add_yesterday(db, "Google Chrome", "Chess - YouTube", hour=10, minutes=30)
    client.post("/api/categories/refresh", params={"day": YESTERDAY.isoformat()})  # Slack by rule

    client.put("/api/categories", json={"app_name": "Google Chrome", "window_title": "Chess - YouTube",
                                        "category": "learning"})
    body = client.get("/api/categories", params={"day": YESTERDAY.isoformat()}).json()

    assert body["category_minutes"] == {"learning": 30, "communication": 20}
    assert body["titles"][0] == {"app_name": "Google Chrome", "window_title": "Chess - YouTube",
                                 "category": "learning", "source": "user", "minutes": 30}


def test_assistant_messages_list_and_mark_read(client, db):
    db.add(AssistantMessage(kind="welcome_back", title="Welcome back!", body="You were away for 20 min."))
    db.commit()

    messages = client.get("/api/assistant/messages", params={"unread_only": True}).json()
    client.post(f"/api/assistant/messages/{messages[0]['id']}/read")

    assert messages[0]["title"] == "Welcome back!"
    assert client.get("/api/assistant/messages", params={"unread_only": True}).json() == []
    assert client.post("/api/assistant/messages/999/read").status_code == 404


def test_clear_history_also_deletes_summaries_messages_and_categories(client, db):
    add_yesterday(db)
    db.add_all([
        DailySummary(day=YESTERDAY, payload={}, source="llm"),
        AssistantMessage(kind="end_of_day", title="t", body="b"),
        TitleCategory(app_name="Code", window_title="digest.py", category="work", source="rule"),
    ])
    db.commit()

    assert client.post("/api/control/clear-history").status_code == 200

    for table in (AppActivity, DailySummary, AssistantMessage, TitleCategory):
        assert db.query(table).count() == 0
