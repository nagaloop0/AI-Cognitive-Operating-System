"""
Unit tests for the notification manager.
subprocess.Popen is replaced by a fake, so no real macOS notification is ever sent.
Run: venv/bin/python -m pytest test/test_notifications.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import notifications
from backend.notifications import NotificationManager


@pytest.fixture
def popen_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(notifications.subprocess, "Popen", lambda *args, **kwargs: calls.append(args))
    return calls


def test_quiet_mode_sends_no_popup(popen_calls):
    manager = NotificationManager()

    sent = manager.dispatch_suggestion("Chrome", "Code", 80, show_popup=False)

    assert sent is True
    assert popen_calls == []


def test_popup_mode_calls_osascript(popen_calls):
    manager = NotificationManager()

    sent = manager.dispatch_suggestion("Chrome", "Code", 80, show_popup=True)

    assert sent is True
    assert popen_calls[0][0][0] == "osascript"


def test_quiet_mode_still_respects_cooldown(popen_calls):
    manager = NotificationManager()

    first = manager.dispatch_suggestion("Chrome", "Code", 80, show_popup=False)
    second = manager.dispatch_suggestion("Chrome", "Code", 80, show_popup=False)

    assert first is True
    assert second is False


def test_global_cooldown_blocks_a_different_suggestion(popen_calls):
    manager = NotificationManager()

    manager.dispatch_suggestion("Chrome", "Code", 80, show_popup=False)
    other = manager.dispatch_suggestion("Code", "Terminal", 70, show_popup=False)

    assert other is False


def test_quotes_in_app_names_are_escaped(popen_calls):
    manager = NotificationManager()

    manager.dispatch_suggestion('My "App"', "Code", 80, show_popup=True)

    script = popen_calls[0][0][2]
    assert '\\"App\\"' in script
