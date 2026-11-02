"""
App and title rules, loaded from a JSON data file instead of being written into the code.
Default file: backend/data/app_rules.json. Use your own copy with APP_RULES_FILE in .env.
"""
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_RULES_FILE = Path(__file__).parent / "data" / "app_rules.json"


@dataclass(frozen=True)
class AppRules:
    app_categories: dict[str, str]       # lower-case app name -> category
    meeting_apps: frozenset[str]
    meeting_title_words: tuple[str, ...]
    media_apps: frozenset[str]
    video_title_words: tuple[str, ...]


def _lower(names) -> frozenset[str]:
    return frozenset(name.casefold() for name in names)


@lru_cache(maxsize=1)
def load_rules(path: str | None = None) -> AppRules:
    raw = json.loads(Path(path or os.getenv("APP_RULES_FILE") or DEFAULT_RULES_FILE).read_text())
    categories = {app.casefold(): category
                  for category, apps in raw["app_categories"].items() for app in apps}
    return AppRules(
        app_categories=categories,
        meeting_apps=_lower(raw["meeting_apps"]),
        meeting_title_words=tuple(word.casefold() for word in raw["meeting_title_words"]),
        media_apps=_lower(raw["media_apps"]),
        video_title_words=tuple(word.casefold() for word in raw["video_title_words"]),
    )
