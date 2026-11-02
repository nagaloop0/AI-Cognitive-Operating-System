"""
Builds the JSON files for the public demo (GitHub Pages) from FAKE data only.

1. A throwaway SQLite database is filled with the invented week from scripts/demo_seed.py.
   The real database is never opened: backend.database.engine and SessionLocal are replaced by tripwires.
2. The real backend code runs on it: habits, day digests, categories, summaries, assistant messages, and
   "Ask your history" for the dashboard's example questions.
3. The API answers are saved to frontend/public/demo-data/*.json; the demo build reads them instead of an API.

The AI texts are written by the local model (Ollama) while this script runs and are stored as samples.
Run on a Mac with Ollama:  venv/bin/python -m scripts.build_demo_data --model qwen2.5:7b
"""
import os
import time

os.environ["TZ"] = "Europe/Berlin"   # same day boundaries on every machine that rebuilds the demo
time.tzset()

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import backend.database as database  # noqa: E402
from backend.ask import answer_question  # noqa: E402
from backend.assistant import end_of_day, welcome_back  # noqa: E402
from backend.llm_client import LLMClient, get_llm_client  # noqa: E402
from backend.models import AppActivity  # noqa: E402
from backend.pattern_engine import MarkovPatternEngine  # noqa: E402
from backend.settings import AssistantSettings  # noqa: E402
from backend.summary import get_daily_summary  # noqa: E402
from backend.tasks import embed_new_titles  # noqa: E402
from scripts.demo_seed import DEMO_DAYS, DEMO_TIMEZONE, DEMO_TODAY, activities_for, all_titles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "frontend" / "public" / "demo-data"
# Must match EXAMPLES in frontend/src/components/AskHistory.vue: only these get stored answers
EXAMPLE_QUESTIONS = ["What did I work on yesterday?", "When did I work on the dashboard?", "How was my focus on Monday?"]


class _Tripwire:
    def __init__(self, name):
        self._name = name

    def __call__(self, *args, **kwargs):
        raise RuntimeError(f"build_demo_data must not use the real database ({self._name})")

    __getattr__ = __call__


def seed(db) -> None:
    rng = random.Random(42)
    zone = ZoneInfo(DEMO_TIMEZONE)
    for index, day in enumerate(DEMO_DAYS):
        for hhmm, app, title, minutes in activities_for(index):
            hours, mins = map(int, hhmm.split(":"))
            start = datetime(day.year, day.month, day.day, hours, mins, tzinfo=zone).astimezone(timezone.utc)
            typing = app in {"Code", "Terminal", "Slack", "Mail"}
            db.add(AppActivity(app_name=app, window_title=title, start_time=start,
                               end_time=start + timedelta(minutes=minutes), duration_seconds=minutes * 60,
                               keystroke_count=rng.randint(30, 90) * minutes if typing else rng.randint(0, 5) * minutes,
                               mouse_click_count=rng.randint(2, 12) * minutes))
    db.commit()


def add_predictions(db) -> None:
    """A few suggestions from the learned habits, with accept/ignore feedback, as the tracker would record."""
    patterns = MarkovPatternEngine.train_patterns(db)
    for i, pattern in enumerate(sorted(patterns, key=lambda p: -p["confidence"])[:6]):
        MarkovPatternEngine.record_prediction(pattern["trigger"], pattern["predicted"],
                                              "accepted" if i % 3 != 2 else "ignored", db)


def write_json(name: str, data) -> None:
    (OUTPUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def check_only_fake_titles(dashboard: dict) -> None:
    allowed = all_titles() | {"(private)"}
    unknown = {item["window_title"] for item in dashboard["timeline"]} - allowed
    if unknown:
        raise RuntimeError(f"Demo data contains titles that are not in demo_seed.py: {unknown}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the demo JSON files from fake data.")
    parser.add_argument("--model", default=None, help="Ollama model for the stored AI samples (default: LLM_MODEL)")
    args = parser.parse_args()

    database.engine = _Tripwire("engine")
    database.SessionLocal = _Tripwire("SessionLocal")

    workdir = Path(tempfile.mkdtemp(prefix="cognitive_demo_"))
    engine = create_engine(f"sqlite:///{workdir / 'demo.db'}")
    assert engine.url.get_backend_name() == "sqlite"
    database.init_db(engine)
    db = sessionmaker(bind=engine)()
    llm = LLMClient(model=args.model) if args.model else LLMClient()
    if not llm.is_available():
        raise SystemExit("Ollama is not running: start it so the stored AI samples can be written.")

    from backend.main import app  # imported after the tripwires are in place
    app.dependency_overrides[database.get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm
    client = TestClient(app, base_url="http://localhost:8000")

    try:
        seed(db)
        add_predictions(db)
        last_day = DEMO_DAYS[-1]
        zone = ZoneInfo(DEMO_TIMEZONE)
        lunch = datetime(last_day.year, last_day.month, last_day.day, 12, 26, tzinfo=zone).astimezone(timezone.utc)
        welcome_back(db, lunch, 54 * 60, AssistantSettings())
        end_of_day(db, llm, last_day)

        OUTPUT.mkdir(parents=True, exist_ok=True)
        for old in OUTPUT.glob("*.json"):
            old.unlink()

        note = (f"Stored AI samples: written by {llm.model} running locally (Ollama) on the fake data, "
                f"generated {datetime.now(timezone.utc):%Y-%m-%d}.")
        for day in DEMO_DAYS:
            summary = get_daily_summary(db, day, llm).model_dump(mode="json")
            if summary["source"] == "llm":
                summary["notice"] = f"Stored sample: written by {llm.model} on a Mac from the fake demo data."
            write_json(f"summary-{day.isoformat()}.json", summary)

        dashboard = client.get("/api/stats/dashboard", params={"limit": 15}).json()
        check_only_fake_titles(dashboard)
        write_json("stats-dashboard.json", dashboard)
        write_json("assistant-messages.json", client.get("/api/assistant/messages", params={"limit": 10}).json())

        embed_new_titles(db, llm)
        samples = [{"question": q, "answer": answer_question(db, llm, q, today=DEMO_TODAY).model_dump(mode="json")}
                   for q in EXAMPLE_QUESTIONS]
        write_json("ask-samples.json", samples)

        write_json("manifest.json", {"days": [d.isoformat() for d in DEMO_DAYS], "latest_day": last_day.isoformat(),
                                     "note": note})
        print(f"Demo data written to {OUTPUT.relative_to(ROOT)}:")
        for path in sorted(OUTPUT.glob("*.json")):
            print(f"  {path.name} ({path.stat().st_size // 1024} KB)")
    finally:
        db.close()
        app.dependency_overrides.clear()
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
