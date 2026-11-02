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


# ---- PostgreSQL integration tests (marker "postgres") ---------------------------------------------
#
# Run them with:  TEST_DATABASE_URL=postgresql+psycopg2://<user>@localhost/cognitive_os_test pytest -m postgres
# Without TEST_DATABASE_URL they skip locally. In CI, REQUIRE_POSTGRES_TESTS=1 turns every skip into a failure.

TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"
REQUIRE_POSTGRES_ENV = "REQUIRE_POSTGRES_TESTS"


def checked_test_database_url(url: str) -> str:
    """Fails hard unless the database name ends in _test, so the real cognitive_os can never be used."""
    from sqlalchemy.engine import make_url

    name = make_url(url).database or ""
    if not name.endswith("_test"):
        pytest.fail(f"Refusing to run integration tests on database '{name}': its name must end in _test.",
                    pytrace=False)
    return url


class _Tripwire:
    """Stands in for the real engine / SessionLocal during integration tests: any use fails the test."""

    def __init__(self, name):
        self._name = name

    def __call__(self, *args, **kwargs):
        raise AssertionError(f"Integration tests must not use backend.database.{self._name} (the real database)")

    def __getattr__(self, attribute):
        raise AssertionError(f"Integration tests must not use backend.database.{self._name} (the real database)")


@pytest.fixture(scope="session")
def pg_engine():
    url = os.getenv(TEST_DATABASE_URL_ENV)
    if not url:
        if os.getenv(REQUIRE_POSTGRES_ENV) == "1":
            pytest.fail(f"{TEST_DATABASE_URL_ENV} is not set, but {REQUIRE_POSTGRES_ENV}=1", pytrace=False)
        pytest.skip(f"{TEST_DATABASE_URL_ENV} not set")
    engine = create_engine(checked_test_database_url(url))
    init_db(engine)  # always this engine, never the default one
    yield engine
    engine.dispose()


def _empty_all_tables(engine):
    from sqlalchemy import text

    from backend.database import Base

    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def pg_db(pg_engine, monkeypatch):
    """A session on the test database. Tables are emptied before (a crashed run cannot break the next one)
    and after each test; the real engine and SessionLocal are replaced by tripwires."""
    import backend.database as database

    monkeypatch.setattr(database, "engine", _Tripwire("engine"))
    monkeypatch.setattr(database, "SessionLocal", _Tripwire("SessionLocal"))
    _empty_all_tables(pg_engine)
    session = sessionmaker(bind=pg_engine)()
    yield session
    session.close()
    _empty_all_tables(pg_engine)


def pytest_sessionfinish(session, exitstatus):
    """In CI (REQUIRE_POSTGRES_TESTS=1) a run of postgres tests that skipped any test, or ran none, must fail."""
    if os.getenv(REQUIRE_POSTGRES_ENV) != "1":
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    skipped = len(reporter.stats.get("skipped", [])) if reporter else 0
    passed = len(reporter.stats.get("passed", [])) if reporter else 0
    if skipped or passed == 0:
        print(f"\n{REQUIRE_POSTGRES_ENV}=1: {skipped} skipped, {passed} passed -> failing the run")
        session.exitstatus = 1
