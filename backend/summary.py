"""
AI daily summary: the local model turns a day digest into a few readable sentences.

Design rules:
- Numbers (time split) are copied from the digest, never from the model, so they cannot be invented.
- The model must answer in a fixed JSON shape; the answer is validated with Pydantic.
- One retry with the validation error explained; if the model is down or still wrong,
  a plain summary is built from the digest (the feature never fails completely).
- Summaries are cached per day in `daily_summary`; today's summary is refreshed after a while.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.categories import categorize_day
from backend.digest import DayDigest, build_day_digest
from backend.llm_client import LLMError, LLMResponseError, LLMTimeoutError, LLMUnavailableError
from backend.models import DailySummary
from backend.settings import load_settings
from backend.timeutil import as_utc, format_minutes, local_today

logger = logging.getLogger("summary")

MAX_ATTEMPTS = 2
PARTIAL_SUMMARY_MAX_AGE = timedelta(minutes=30)   # today's summary is remade after this

TONE_STYLE = {
    "friendly": "warm and encouraging, like a kind colleague",
    "strict": "short and direct, like a focused coach; no small talk",
    "funny": "light and playful, with at most one small joke",
}

SYSTEM_PROMPT = """You summarize one day of computer work for the person who did it.
Rules:
- Use ONLY the facts in the activity report. Never invent tasks, files, people or numbers.
- Topics come from the window titles: project names, file names, page titles. App names alone are not topics.
- Be honest about the numbers: if active time or focus blocks are short, say so; do not call it productive.
- Write in English, in a {tone_style} tone. Address the person as "you".
- Example of the style (a different person's day, do not copy it): headline "Refactoring the payment API",
  focus areas ["payment_service.py", "Stripe webhook docs"].
Answer only with JSON that matches the given schema."""


class SummaryText(BaseModel):
    """The part written by the model. Field descriptions are part of the JSON schema the model receives."""
    headline: str = Field(min_length=3, max_length=120,
                          description="At most 12 words naming the main work topic from the window titles. Never a date.")
    focus_areas: list[str] = Field(min_length=1, max_length=4,
                                   description="1 to 4 work topics (project, file or page names) taken from the "
                                               "window titles, not app names.")
    insight: str = Field(min_length=3, max_length=300,
                         description="One honest sentence about how the day went, using the numbers.")
    suggestion: str = Field(min_length=3, max_length=300,
                            description="One concrete, practical sentence for tomorrow that follows from the insight.")


class TimeSplit(BaseModel):
    app_name: str
    minutes: int


class DailySummaryResult(BaseModel):
    day: date
    headline: str
    focus_areas: list[str]
    insight: str
    suggestion: str
    time_split: list[TimeSplit]
    active_minutes: int
    category_minutes: dict[str, int]
    source: Literal["llm", "fallback"]
    model: str | None
    attempts: int
    is_partial: bool
    generated_at: datetime
    notice: str | None = None


def generate_summary(digest: DayDigest, llm, tone: str = "friendly", is_partial: bool = False) -> DailySummaryResult:
    """Asks the model for the written part; falls back to a plain summary if that is not possible."""
    if digest.is_empty:
        return _build_result(digest, fallback_text(digest), "fallback", None, 0, is_partial,
                             notice="No activity recorded for this day.")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(tone_style=TONE_STYLE.get(tone, TONE_STYLE["friendly"]))},
        {"role": "user", "content": "Activity report:\n" + digest.to_prompt_text()},
    ]
    schema = SummaryText.model_json_schema()
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = llm.chat(messages, json_schema=schema)
            text = SummaryText.model_validate(raw)
            return _build_result(digest, text, "llm", llm.model, attempt, is_partial)
        except (LLMUnavailableError, LLMTimeoutError) as e:
            logger.warning("Summary falls back to digest: %s", e)
            return _build_result(digest, fallback_text(digest), "fallback", None, attempt, is_partial,
                                 notice=f"AI not available: {e}")
        except (LLMResponseError, ValidationError) as e:
            last_error = str(e)[:300]
            logger.warning("Summary attempt %s invalid: %s", attempt, last_error)
            # Tell the model exactly what was wrong, then ask again
            messages = messages + [{
                "role": "user",
                "content": f"Your last answer was invalid ({last_error}). Answer again with valid JSON only.",
            }]

    return _build_result(digest, fallback_text(digest), "fallback", None, MAX_ATTEMPTS, is_partial,
                         notice=f"AI answer was invalid twice: {last_error}")


def fallback_text(digest: DayDigest) -> SummaryText:
    """A plain, rule-based summary from the digest numbers. Used when the model cannot help."""
    if digest.is_empty:
        return SummaryText(headline="No activity recorded", focus_areas=["Nothing tracked"],
                           insight="The tracker did not record any activity for this day.",
                           suggestion="Start the tracker (python -m backend.driver) to get a summary.")
    top = digest.apps[0]
    focus = [f"{app.app_name}: {app.top_titles[0]}" if app.top_titles else app.app_name for app in digest.apps[:3]]
    if digest.longest_focus:
        f = digest.longest_focus
        insight = f"Your longest focus was {format_minutes(f.minutes)} in {f.app_name} ({f.start:%H:%M}-{f.end:%H:%M})."
    else:
        insight = f"You switched apps {digest.app_switches} times with no long focus block."
    if digest.active_minutes >= 180 and digest.break_minutes < 15:
        suggestion = "Plan a short break about every 90 minutes."
    else:
        suggestion = "Start tomorrow with the task from your longest focus block."
    return SummaryText(headline=f"{format_minutes(digest.active_minutes)} active, mostly in {top.app_name}",
                       focus_areas=focus, insight=insight, suggestion=suggestion)


def _build_result(digest, text: SummaryText, source, model, attempts, is_partial, notice=None) -> DailySummaryResult:
    return DailySummaryResult(
        day=digest.day,
        **text.model_dump(),
        time_split=[TimeSplit(app_name=a.app_name, minutes=a.minutes) for a in digest.apps],
        active_minutes=digest.active_minutes,
        category_minutes=digest.category_minutes,
        source=source,
        model=model,
        attempts=attempts,
        is_partial=is_partial,
        generated_at=datetime.now(timezone.utc),
        notice=notice,
    )


def get_daily_summary(db: Session, day: date, llm, refresh: bool = False) -> DailySummaryResult:
    """Cached summary for a local day. A finished day is made once; today is remade after 30 minutes.
    Fallback summaries are not cached, so the next request tries the model again."""
    today = local_today()
    if day > today:
        raise ValueError("Cannot summarize a day in the future.")
    is_partial = day == today

    row = db.query(DailySummary).filter(DailySummary.day == day).first()
    if row and not refresh and not _is_stale(row):
        return DailySummaryResult.model_validate(row.payload)

    settings = load_settings(db)
    _categorize_quietly(db, day, llm)
    digest = build_day_digest(db, day, settings.private_apps)
    result = generate_summary(digest, llm, tone=settings.tone, is_partial=is_partial)

    if result.source == "llm" or digest.is_empty:
        payload = result.model_dump(mode="json")
        if row:
            row.payload, row.source, row.model, row.is_partial = payload, result.source, result.model, is_partial
            row.created_at = datetime.now(timezone.utc)
        else:
            db.add(DailySummary(day=day, payload=payload, source=result.source, model=result.model,
                                is_partial=is_partial, created_at=datetime.now(timezone.utc)))
        db.commit()
    return result


def _is_stale(row: DailySummary) -> bool:
    if not row.is_partial:
        return False
    return datetime.now(timezone.utc) - as_utc(row.created_at) > PARTIAL_SUMMARY_MAX_AGE


def _categorize_quietly(db: Session, day: date, llm) -> None:
    """Labels new titles first, so the summary can show work / learning / fun minutes."""
    try:
        categorize_day(db, day, llm)
    except LLMError as e:
        logger.info("Categories skipped: %s", e)
