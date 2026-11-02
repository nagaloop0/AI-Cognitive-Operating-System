"""
Guards for the public demo files (frontend/public/demo-data, built by scripts/build_demo_data.py):
they may only contain the invented week from scripts/demo_seed.py, never real or personal data.
"""
import json
import os
import re
from pathlib import Path

import pytest

from scripts.demo_seed import DEMO_DAYS, all_titles

DEMO_DATA = Path(__file__).resolve().parent.parent / "frontend" / "public" / "demo-data"
# Personal words are NOT written here (this file is public): set them locally, comma-separated, e.g.
#   DEMO_FORBIDDEN_WORDS="firstname,lastname,employer" venv/bin/python -m pytest test/test_demo_data.py
FORBIDDEN_WORDS = [w.strip().casefold() for w in os.getenv("DEMO_FORBIDDEN_WORDS", "").split(",") if w.strip()]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

pytestmark = pytest.mark.skipif(not DEMO_DATA.exists(), reason="demo data not built")


def load(name):
    return json.loads((DEMO_DATA / name).read_text())


def test_no_email_addresses_in_any_demo_file():
    for path in DEMO_DATA.glob("*.json"):
        assert not EMAIL.search(path.read_text()), f"{path.name} contains an email address"


@pytest.mark.skipif(not FORBIDDEN_WORDS, reason="DEMO_FORBIDDEN_WORDS not set (set it locally)")
def test_no_personal_words_in_any_demo_file():
    for path in DEMO_DATA.glob("*.json"):
        text = path.read_text().casefold()
        for word in FORBIDDEN_WORDS:
            assert word not in text, f"{path.name} contains a forbidden word"


def test_timeline_titles_all_come_from_the_fake_seed():
    titles = {item["window_title"] for item in load("stats-dashboard.json")["timeline"]}

    assert titles <= all_titles() | {"(private)"}


def test_ask_sources_all_come_from_the_fake_seed():
    for sample in load("ask-samples.json"):
        assert {s["window_title"] for s in sample["answer"]["sources"]} <= all_titles()


def test_one_summary_per_demo_day_and_the_manifest_matches():
    manifest = load("manifest.json")

    assert manifest["days"] == [d.isoformat() for d in DEMO_DAYS]
    for day in manifest["days"]:
        assert load(f"summary-{day}.json")["day"] == day


def test_stored_ai_samples_are_labelled():
    for day in load("manifest.json")["days"]:
        summary = load(f"summary-{day}.json")
        if summary["source"] == "llm":
            assert summary["notice"].startswith("Stored sample:")
