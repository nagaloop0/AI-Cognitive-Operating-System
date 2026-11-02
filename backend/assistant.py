"""
The assistant's messages: "welcome back" after an absence and the end-of-day summary.
Messages are stored in `assistant_message` and shown in the dashboard; with voice on they are also spoken.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from backend.digest import load_segments
from backend.models import AssistantMessage
from backend.privacy import PRIVATE_TITLE, redact
from backend.settings import AssistantSettings
from backend.summary import get_daily_summary
from backend.timeutil import format_minutes, local_day_bounds, local_tz

logger = logging.getLogger("assistant")

MessageKind = Literal["welcome_back", "end_of_day", "nudge", "unread"]

GREETING = {"friendly": "Welcome back!", "strict": "Back to work.", "funny": "Look who's back!"}
CONTEXT_WINDOW = timedelta(minutes=60)   # what counts as "what you were doing before the break"


def post_message(db: Session, kind: MessageKind, title: str, body: str) -> AssistantMessage:
    message = AssistantMessage(kind=kind, title=title, body=body, created_at=datetime.now(timezone.utc))
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def sent_on(db: Session, kind: str, day: date) -> bool:
    start, end = local_day_bounds(day)
    return (db.query(AssistantMessage)
            .filter(AssistantMessage.kind == kind, AssistantMessage.created_at >= start,
                    AssistantMessage.created_at < end)
            .first() is not None)


def welcome_back(db: Session, left_at: datetime, away_seconds: float, settings: AssistantSettings) -> AssistantMessage:
    """Reminds you what you were doing before the break. Plain facts, no model: it must be instant."""
    segments = load_segments(db, left_at - CONTEXT_WINDOW, left_at)
    seconds = defaultdict(float)
    for seg in segments:
        if seg.title != PRIVATE_TITLE:
            seconds[(seg.app_name, redact(seg.title))] += seg.seconds

    greeting = GREETING.get(settings.tone, GREETING["friendly"])
    body = f"You were away for {format_minutes(round(away_seconds / 60))}."
    if seconds:
        (app_name, title), _ = max(seconds.items(), key=lambda item: item[1])
        body += f" Before the break you were in {app_name}" + (f": {title}." if title else ".")
    return post_message(db, "welcome_back", greeting, body)


def end_of_day(db: Session, llm, day: date) -> AssistantMessage:
    summary = get_daily_summary(db, day, llm, refresh=True)
    body = f"{summary.insight}\nTomorrow: {summary.suggestion}"
    return post_message(db, "end_of_day", summary.headline, body)


def local_now() -> datetime:
    return datetime.now(local_tz())
