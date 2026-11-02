"""
Shared test helpers: an in-memory SQLite database and a fake language model.
pytest loads this file automatically before the tests in this folder.
"""
import os
import sys
from collections import deque
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import init_db
from backend.llm_client import LLMResponseError
from backend.models import EMBEDDING_DIMENSIONS, AppActivity

UTC = timezone.utc


@pytest.fixture
def db():
    # StaticPool = one shared connection, so the API thread in API tests sees the same in-memory data
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class FakeLLM:
    """Stands in for LLMClient. Queue answers (dicts, strings or exceptions); every call takes the next one."""

    def __init__(self, *answers, model="fake-model"):
        self.model = model
        self.answers = deque(answers)
        self.calls: list[dict] = []
        self.vectors: dict[str, list[float]] = {}

    def chat(self, messages, json_schema=None, temperature=0.2):
        self.calls.append({"messages": messages, "json_schema": json_schema})
        if not self.answers:
            raise LLMResponseError("FakeLLM has no answer queued")
        answer = self.answers.popleft()
        if isinstance(answer, Exception):
            raise answer
        return answer

    def chat_message(self, payload):
        self.calls.append(payload)
        answer = self.answers.popleft()
        if isinstance(answer, Exception):
            raise answer
        return answer

    def embed(self, texts):
        return [padded(self.vectors.get(text, [0.0, 0.0, 1.0])) for text in texts]

    def is_available(self):
        return True


@pytest.fixture
def fake_llm():
    return FakeLLM()


def padded(vector):
    """A full-size embedding: the given numbers first, zeros after (same length as the real model)."""
    return list(vector) + [0.0] * (EMBEDDING_DIMENSIONS - len(vector))


def add_activity(db, app, title, start, minutes, keys=0):
    """One activity row from `start` (an aware datetime) lasting `minutes`."""
    end = start + timedelta(minutes=minutes)
    row = AppActivity(app_name=app, window_title=title, start_time=start, end_time=end,
                      duration_seconds=int(minutes * 60), keystroke_count=keys)
    db.add(row)
    db.commit()
    return end


def at(day: str, hhmm: str) -> datetime:
    """UTC datetime from '2026-10-05' and '09:30' (tests run their days in UTC)."""
    return datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=UTC)
