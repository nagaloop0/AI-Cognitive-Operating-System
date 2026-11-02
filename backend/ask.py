"""
"Ask your history": answers questions like "What did I work on Tuesday?" from your own activity (RAG).

Retrieval-Augmented Generation in three steps:
1. Retrieve by time: dates in the question ("yesterday", "Tuesday", "2026-10-29") pick the day digests.
2. Retrieve by meaning: the question is embedded and the closest window titles are found (pgvector),
   with the minutes spent on each of them per day.
3. Generate: the local model answers ONLY from that context; if the answer is not there, it says so.
"""
import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.digest import build_day_digest, load_segments
from backend.llm_client import LLMResponseError
from backend.privacy import redact
from backend.settings import load_settings
from backend.tasks import QUERY_PREFIX, similar_titles
from backend.timeutil import format_minutes, local_day_bounds, local_today, local_tz

logger = logging.getLogger("ask")

DEFAULT_LOOKBACK_DAYS = 7
SOURCE_LOOKBACK_DAYS = 30
MIN_SIMILARITY = 0.60
MIN_SOURCE_SECONDS = 10
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

SYSTEM_PROMPT = """You answer questions about the user's own computer activity.
Use ONLY the context below (day reports and related window titles).
Only say the user worked on something if it appears in the window titles of the context.
If the answer is not in the context, say "I can't find that in your history."
Mention days and durations when they help. Answer in at most 4 short sentences, addressing the user as "you"."""


class AskSource(BaseModel):
    day: date
    app_name: str
    window_title: str
    seconds: int


class AskAnswer(BaseModel):
    question: str
    answer: str
    days: list[date]
    sources: list[AskSource]


def resolve_days(question: str, today: date) -> list[date]:
    """Dates mentioned in the question, newest first; the last 7 days if none are mentioned."""
    text = question.casefold()
    days: set[date] = set()
    for iso in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text):
        try:
            days.add(date.fromisoformat(iso))
        except ValueError:
            pass
    if re.search(r"\btoday\b", text):
        days.add(today)
    if re.search(r"\byesterday\b", text):
        days.add(today - timedelta(days=1))
    for index, name in enumerate(WEEKDAYS):
        if re.search(rf"\b{name}\b", text):
            back = (today.weekday() - index) % 7   # the most recent such day, today included
            if "last" in text and back == 0:
                back = 7
            days.add(today - timedelta(days=back))
    if "last week" in text:
        days.update(today - timedelta(days=7 + i) for i in range(7))
    elif "this week" in text:
        days.update(today - timedelta(days=i) for i in range(today.weekday() + 1))
    if not days:
        days = {today - timedelta(days=i) for i in range(DEFAULT_LOOKBACK_DAYS)}
    return sorted((d for d in days if d <= today), reverse=True)


def answer_question(db: Session, llm, question: str, today: date | None = None) -> AskAnswer:
    """Raises LLMUnavailableError / LLMTimeoutError when the model is down (the API turns that into 503)."""
    today = today or local_today()
    days = resolve_days(question, today)
    private_apps = load_settings(db).private_apps

    digests = [d for d in (build_day_digest(db, day, private_apps) for day in days) if not d.is_empty]
    sources = _related_titles(db, llm, question, today)

    context = ["Day reports:"]
    context += [d.to_prompt_text() for d in digests] or ["(no activity on those days)"]
    if sources:
        context.append("Window titles related to the question (day, app, title, time spent):")
        context += [f"- {s.day:%a %Y-%m-%d} | {s.app_name} | {s.window_title} | {format_seconds(s.seconds)}"
                    for s in sources]
    else:
        context.append("No window titles match the question.")

    answer = llm.chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Context:\n" + "\n\n".join(context) + f"\n\nQuestion: {question}"},
    ])
    return AskAnswer(question=question, answer=str(answer).strip(), days=[d.day for d in digests], sources=sources)


def _related_titles(db: Session, llm, question: str, today: date, k: int = 8) -> list[AskSource]:
    """Titles closest in meaning to the question, with minutes per day over the last 30 days."""
    try:
        query_vector = llm.embed([QUERY_PREFIX + question])[0]
    except LLMResponseError as e:
        logger.info("Semantic search skipped (embedding model missing?): %s", e)
        return []
    matches = {(row.app_name, row.window_title) for row, score in similar_titles(db, query_vector, k)
               if score >= MIN_SIMILARITY}
    if not matches:
        return []

    start, _ = local_day_bounds(today - timedelta(days=SOURCE_LOOKBACK_DAYS))
    _, end = local_day_bounds(today)
    seconds: dict[tuple[date, str, str], float] = defaultdict(float)
    for seg in load_segments(db, start, end):
        if (seg.app_name, seg.title) in matches:
            seconds[(seg.start.astimezone(local_tz()).date(), seg.app_name, seg.title)] += seg.seconds
    sources = [AskSource(day=day, app_name=app, window_title=redact(title), seconds=round(s))
               for (day, app, title), s in seconds.items() if s >= MIN_SOURCE_SECONDS]
    return sorted(sources, key=lambda s: (s.day, s.seconds), reverse=True)[:12]


def format_seconds(seconds: int) -> str:
    return f"{seconds} s" if seconds < 60 else format_minutes(round(seconds / 60))
