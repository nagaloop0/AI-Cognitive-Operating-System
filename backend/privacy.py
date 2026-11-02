"""
Privacy guardrails for window titles.

Two layers:
1. Before storing: titles of private apps (and private/banking windows) are never saved.
2. Before any title reaches the language model: emails and long numbers are masked and the title is shortened.
"""
import re

PRIVATE_TITLE = "(private)"
PRIVATE_APP_GROUP = "Private apps"
MAX_TITLE_CHARS = 80


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# 8+ digits, optionally split by spaces or dashes: card, account and phone numbers
LONG_NUMBER_PATTERN = re.compile(r"\b\d(?:[ -]?\d){7,}\b")


def is_private_app(app_name: str | None, private_apps: list[str]) -> bool:
    return bool(app_name) and app_name.casefold() in {app.casefold() for app in private_apps}


def is_private_window(app_name: str | None, title: str | None, private_apps: list[str],
                      private_words: list[str]) -> bool:
    """A private app, or any window whose title contains a private word (incognito, bank...)."""
    if is_private_app(app_name, private_apps):
        return True
    lowered = (title or "").casefold()
    return any(word.casefold() in lowered for word in private_words)


def title_for_storage(app_name: str | None, title: str | None, private_apps: list[str],
                      private_words: list[str]) -> str:
    """The title as it may be saved in the database."""
    if is_private_window(app_name, title, private_apps, private_words):
        return PRIVATE_TITLE
    return title or ""


def redact(text: str | None, max_chars: int = MAX_TITLE_CHARS) -> str:
    """Masks personal data and shortens the text before it goes into a prompt."""
    if not text:
        return ""
    cleaned = EMAIL_PATTERN.sub("[email]", text)
    cleaned = LONG_NUMBER_PATTERN.sub("[number]", cleaned)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned
