"""
Categories for window titles: work, learning, fun, communication, other.

1. Rules first: apps with one clear purpose (backend/data/app_rules.json) need no model.
2. The rest (mostly browser tabs) go to the local model in small batches.
3. A user correction is stored with source "user" and is never overwritten.
Each (app, title) pair is labelled once and reused for every later day.
"""
import logging
from datetime import date
from typing import Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from backend.digest import load_segments
from backend.llm_client import LLMResponseError
from backend.models import TitleCategory
from backend.privacy import PRIVATE_TITLE, redact
from backend.rules import load_rules
from backend.timeutil import local_day_bounds

logger = logging.getLogger("categories")

Category = Literal["work", "learning", "fun", "communication", "other"]
CATEGORIES: tuple[str, ...] = ("work", "learning", "fun", "communication", "other")
BATCH_SIZE = 15


PROMPT = """Classify each window title into exactly one category:
- work: programming, documents, spreadsheets, project tools, job tasks, job search (CVs, job ads, applications)
- learning: tutorials, courses, documentation, reference pages (e.g. Wikipedia), "how to" and "what is" pages,
  educational videos. A YouTube video is learning when its title is about a skill or a technology.
- fun: entertainment, games, music, sports, movies, series, social media browsing
- communication: email, chat, calls, meetings
- other: shopping, system settings, file browsing, anything unclear
Decide from the title's topic, not from the app. Return one label per title, using the title's index."""


class _Label(BaseModel):
    index: int
    category: Category


class _LabelBatch(BaseModel):
    labels: list[_Label]


def rule_category(app_name: str, title: str) -> str | None:
    """Category from the app alone (backend/data/app_rules.json), or None when the title decides."""
    known = load_rules().app_categories.get(app_name.casefold())
    if title == PRIVATE_TITLE:
        return known or "other"
    return known


def categorize_day(db: Session, day: date, llm) -> int:
    """Labels every (app, title) used on `day` that has no label yet. Returns how many were added.
    Raises LLMUnavailableError / LLMTimeoutError when the model is down (callers decide what to do)."""
    start, end = local_day_bounds(day)
    pairs = {(s.app_name, s.title) for s in load_segments(db, start, end)}
    known = {(r.app_name, r.window_title) for r in db.query(TitleCategory).all()}
    todo = sorted(pairs - known)

    added = 0
    needs_model = []
    for app_name, title in todo:
        category = rule_category(app_name, title)
        if category:
            db.add(TitleCategory(app_name=app_name, window_title=title, category=category, source="rule"))
            added += 1
        else:
            needs_model.append((app_name, title))
    db.commit()

    for i in range(0, len(needs_model), BATCH_SIZE):
        batch = needs_model[i:i + BATCH_SIZE]
        labels = classify_titles(llm, batch)
        for index, category in labels.items():
            app_name, title = batch[index]
            db.add(TitleCategory(app_name=app_name, window_title=title, category=category, source="llm"))
            added += 1
        db.commit()
    return added


def classify_titles(llm, batch: list[tuple[str, str]]) -> dict[int, str]:
    """Asks the model for one category per (app, title); returns {index: category}. Empty on a bad answer."""
    listing = "\n".join(f"{i}. [{app}] {redact(title) or '(no title)'}" for i, (app, title) in enumerate(batch))
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"Titles:\n{listing}"},
    ]
    try:
        raw = llm.chat(messages, json_schema=_batch_schema(len(batch)), temperature=0)
        parsed = _LabelBatch.model_validate(raw)
    except (LLMResponseError, ValidationError) as e:
        logger.warning("Category batch skipped (will retry next time): %s", e)
        return {}
    # Ignore indexes the model made up; keep the first label per index
    labels: dict[int, str] = {}
    for label in parsed.labels:
        if 0 <= label.index < len(batch) and label.index not in labels:
            labels[label.index] = label.category
    return labels


def _batch_schema(size: int) -> dict:
    """Exactly one label per title. Without minItems a model may legally answer {"labels": []}
    (qwen2.5:7b did, scoring 0% in the first evaluation run)."""
    schema = _LabelBatch.model_json_schema()
    schema["properties"]["labels"].update(minItems=size, maxItems=size)
    return schema


def set_category(db: Session, app_name: str, window_title: str, category: str) -> TitleCategory:
    """A user correction: stored with source "user", so it is never replaced by a rule or the model."""
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
    row = (db.query(TitleCategory)
           .filter(TitleCategory.app_name == app_name, TitleCategory.window_title == window_title).first())
    if row:
        row.category, row.source = category, "user"
    else:
        row = TitleCategory(app_name=app_name, window_title=window_title, category=category, source="user")
        db.add(row)
    db.commit()
    return row


def category_of(db: Session, app_name: str, window_title: str) -> str | None:
    row = (db.query(TitleCategory)
           .filter(TitleCategory.app_name == app_name, TitleCategory.window_title == window_title).first())
    return row.category if row else None
