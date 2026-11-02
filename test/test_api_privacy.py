"""
Privacy tests for the FastAPI app.
The real database is replaced by a throwaway in-memory SQLite database, so PostgreSQL is never touched.
Run: venv/bin/python -m pytest test/test_api_privacy.py -v
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import Base, get_db
from backend.main import app
from backend.models import AppActivity, HabitPattern, AIPrediction

DASHBOARD = "http://localhost:5173"
OTHER_WEBSITE = "https://some-website.example"


@pytest.fixture
def db():
    # StaticPool keeps one connection, so the API (running in another thread) sees the same in-memory database
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    # Host must be a loopback name (see block_other_websites); TestClient's default is 'testserver'
    yield TestClient(app, base_url="http://localhost:8000")
    app.dependency_overrides.clear()


def test_other_website_cannot_read_activity(client):
    response = client.get("/api/stats/timeline", headers={"Origin": OTHER_WEBSITE})

    assert response.status_code == 403


def test_other_website_cannot_clear_history(client, db):
    db.add(AppActivity(app_name="Code", window_title="main.py"))
    db.commit()

    response = client.post("/api/control/clear-history", headers={"Origin": OTHER_WEBSITE})

    assert response.status_code == 403
    assert db.query(AppActivity).count() == 1


def test_dashboard_can_read_activity(client):
    response = client.get("/api/stats/timeline", headers={"Origin": DASHBOARD})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DASHBOARD


def test_request_without_origin_is_allowed(client):
    # Vite's proxy, curl and scripts send no browser Origin header
    response = client.get("/api/stats/summary")

    assert response.status_code == 200


def test_clear_history_deletes_activities_habits_and_predictions(client, db):
    db.add(AppActivity(app_name="Code", window_title="main.py"))
    db.add(HabitPattern(trigger_sequence="Chrome", predicted_action="Code", occurrence_count=3, confidence=0.75))
    db.add(AIPrediction(trigger_sequence="Chrome", suggested_action="Code", status="accepted"))
    db.commit()

    response = client.post("/api/control/clear-history", headers={"Origin": DASHBOARD})

    assert response.status_code == 200
    assert db.query(AppActivity).count() == 0
    assert db.query(HabitPattern).count() == 0
    assert db.query(AIPrediction).count() == 0


def test_api_docs_page_can_call_the_api(client):
    # Swagger UI at http://localhost:8000/docs sends its own address as Origin on POST requests
    response = client.post("/api/patterns/retrain", headers={"Origin": "http://localhost:8000",
                                                             "Host": "localhost:8000"})

    assert response.status_code == 200


def test_dns_rebinding_is_blocked(client):
    # An attacker's domain pointed at 127.0.0.1: Origin and Host match, but the host is not localhost
    response = client.get("/api/stats/timeline", headers={"Origin": "http://evil.example:8000",
                                                          "Host": "evil.example:8000"})

    assert response.status_code == 403


def test_dns_rebinding_without_origin_is_blocked(client):
    # A same-origin GET on the rebound domain sends no Origin at all; the Host alone must stop it
    response = client.get("/api/stats/timeline", headers={"Host": "attacker.example:8000"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Host not allowed"}


def test_vite_proxy_host_is_allowed(client):
    # vite.config.ts proxies /api with changeOrigin: true, so the API sees Host 127.0.0.1:8000
    assert client.get("/api/stats/summary", headers={"Host": "127.0.0.1:8000"}).status_code == 200


def test_ipv6_loopback_is_parsed_but_only_allowed_when_trusted(client):
    assert client.get("/api/stats/summary", headers={"Host": "[::1]:8000"}).status_code == 403
