"""
User settings for the assistant, stored as key/value rows in the existing `user_preference` table.
Every value has a default, so a fresh database works without any setup.
"""
import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from backend.models import UserPreference

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Defaults for a fresh install; each user changes them with PUT /api/settings
DEFAULT_PRIVATE_APPS = [
    "WhatsApp", "Signal", "Messages", "Telegram", "Passwords", "1Password", "1Password 7", "Keychain Access",
]
DEFAULT_PRIVATE_TITLE_WORDS = ["incognito", "private browsing", "inprivate", "online banking", "bank", "password"]


class AssistantSettings(BaseModel):
    # Privacy
    private_apps: list[str] = Field(default_factory=lambda: list(DEFAULT_PRIVATE_APPS))
    private_title_words: list[str] = Field(default_factory=lambda: list(DEFAULT_PRIVATE_TITLE_WORDS))
    # Presence: no keyboard/mouse input for this long = idle (calls and videos get a longer limit)
    idle_timeout_seconds: int = Field(120, ge=20, le=3600)
    # Smart timing, in the Mac's local time zone (moving to another country just works)
    summary_time: str = "19:00"           # end-of-day summary from this local time...
    summary_latest_time: str = "23:35"    # ...but never later than this, even if still working
    break_minutes: int = Field(5, ge=1, le=60)       # no input this long = a break (good moment to speak)
    away_minutes: int = Field(15, ge=1, le=240)      # away this long = "welcome back" on return
    # Personal assistant
    tone: Literal["friendly", "strict", "funny"] = "friendly"
    interests: list[str] = Field(default_factory=lambda: ["tech news", "football", "movies"])
    fun_limit_minutes: int = Field(20, ge=5, le=240)          # fun in a row before a nudge back to work
    work_break_reminder_minutes: int = Field(120, ge=30, le=480)  # work in a row before a break nudge
    voice_enabled: bool = False

    @field_validator("summary_time", "summary_latest_time")
    @classmethod
    def check_time(cls, value: str) -> str:
        if not TIME_PATTERN.match(value):
            raise ValueError("use 24-hour HH:MM, e.g. 19:00")
        return value


SETTING_KEYS = tuple(AssistantSettings.model_fields)


def load_settings(db: Session) -> AssistantSettings:
    """Reads every stored setting; missing or broken values fall back to the default."""
    rows = db.query(UserPreference).filter(UserPreference.key.in_(SETTING_KEYS)).all()
    stored = {}
    for row in rows:
        try:
            stored[row.key] = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            continue
    try:
        return AssistantSettings(**stored)
    except ValidationError:
        # One bad stored value must not break the whole app: keep only the valid ones
        valid = {}
        for key, value in stored.items():
            try:
                AssistantSettings(**{key: value})
                valid[key] = value
            except ValidationError:
                pass
        return AssistantSettings(**valid)


def save_settings(db: Session, updates: dict) -> AssistantSettings:
    """Validates the changed values together with the current ones, then stores only the changes."""
    unknown = set(updates) - set(SETTING_KEYS)
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(sorted(unknown))}")
    merged = load_settings(db).model_dump() | updates
    new_settings = AssistantSettings(**merged)  # raises ValidationError on bad values

    for key in updates:
        value = json.dumps(getattr(new_settings, key))
        row = db.query(UserPreference).filter(UserPreference.key == key).first()
        if row:
            row.value = value
        else:
            db.add(UserPreference(key=key, value=value))
    db.commit()
    return new_settings
