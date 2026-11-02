"""
"When to speak" rules. Pure functions with no database or model, so every rule is easy to test.

- Idle: no input for a while = away; calls and videos get a much longer limit (you watch, you do not type).
- End of day: from `summary_time`, wait for a break; never later than `summary_latest_time`.
- Welcome back: only after a real absence (`away_minutes`), not after a pause to think.
"""
from datetime import datetime, time

from backend.rules import load_rules
from backend.settings import AssistantSettings

PASSIVE_IDLE_SECONDS = 30 * 60   # calls and videos: you watch instead of type


def parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def is_meeting(app_name: str | None, title: str | None) -> bool:
    rules, lowered = load_rules(), (title or "").casefold()
    return (app_name or "").casefold() in rules.meeting_apps or any(w in lowered for w in rules.meeting_title_words)


def is_passive(app_name: str | None, title: str | None) -> bool:
    """Watching or listening: no keyboard input is expected."""
    rules, lowered = load_rules(), (title or "").casefold()
    return (is_meeting(app_name, title)
            or (app_name or "").casefold() in rules.media_apps
            or any(word in lowered for word in rules.video_title_words))


def idle_threshold_seconds(app_name: str | None, title: str | None, settings: AssistantSettings) -> int:
    return PASSIVE_IDLE_SECONDS if is_passive(app_name, title) else settings.idle_timeout_seconds


def is_end_of_day_due(now_local: datetime, seconds_since_input: float, settings: AssistantSettings,
                      already_sent_today: bool) -> bool:
    if already_sent_today or now_local.time() < parse_hhmm(settings.summary_time):
        return False
    on_break = seconds_since_input >= settings.break_minutes * 60
    too_late = now_local.time() >= parse_hhmm(settings.summary_latest_time)
    return on_break or too_late


def is_welcome_back(away_seconds: float, settings: AssistantSettings) -> bool:
    return away_seconds >= settings.away_minutes * 60
