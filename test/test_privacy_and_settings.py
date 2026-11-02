"""
Tests for the privacy guardrails (backend/privacy.py) and the settings store (backend/settings.py).
"""
import pytest
from pydantic import ValidationError

from backend.models import UserPreference
from backend.privacy import PRIVATE_TITLE, redact, title_for_storage
from backend.settings import AssistantSettings, load_settings, save_settings

PRIVATE_APPS = ["WhatsApp", "1Password"]
PRIVATE_WORDS = ["incognito", "bank"]


def test_private_app_title_is_never_stored():
    assert title_for_storage("WhatsApp", "Chat with Mum", PRIVATE_APPS, PRIVATE_WORDS) == PRIVATE_TITLE


def test_private_app_match_ignores_case():
    assert title_for_storage("whatsapp", "Chat", PRIVATE_APPS, PRIVATE_WORDS) == PRIVATE_TITLE


def test_incognito_and_bank_windows_are_private_in_any_app():
    assert title_for_storage("Google Chrome", "New Incognito Tab", PRIVATE_APPS, PRIVATE_WORDS) == PRIVATE_TITLE
    assert title_for_storage("Safari", "Online Banking - My Bank", PRIVATE_APPS, PRIVATE_WORDS) == PRIVATE_TITLE


def test_normal_title_is_stored_unchanged():
    assert title_for_storage("Code", "digest.py — explore_p", PRIVATE_APPS, PRIVATE_WORDS) == "digest.py — explore_p"


def test_redact_masks_emails_and_long_numbers():
    title = "Inbox (5) - jane.doe@example.com - Card 4111 1111 1111 1111"

    assert redact(title) == "Inbox (5) - [email] - Card [number]"


def test_redact_keeps_short_numbers_and_shortens_long_titles():
    assert redact("Inbox (5)") == "Inbox (5)"
    long_title = "a" * 200
    assert len(redact(long_title)) == 80
    assert redact(long_title).endswith("…")


def test_settings_have_defaults_on_empty_database(db):
    settings = load_settings(db)

    assert settings.summary_time == "19:00"
    assert settings.tone == "friendly"
    assert "WhatsApp" in settings.private_apps


def test_saved_settings_are_loaded_back(db):
    save_settings(db, {"tone": "strict", "away_minutes": 30, "interests": ["chess"]})

    settings = load_settings(db)
    assert (settings.tone, settings.away_minutes, settings.interests) == ("strict", 30, ["chess"])


def test_invalid_setting_is_rejected_and_nothing_is_saved(db):
    with pytest.raises(ValidationError):
        save_settings(db, {"summary_time": "7pm"})

    assert db.query(UserPreference).count() == 0


def test_unknown_setting_is_rejected(db):
    with pytest.raises(ValueError, match="Unknown setting"):
        save_settings(db, {"color": "blue"})


def test_one_broken_stored_value_does_not_break_the_others(db):
    db.add(UserPreference(key="tone", value='"angry"'))
    db.add(UserPreference(key="away_minutes", value="45"))
    db.commit()

    settings = load_settings(db)

    assert settings.tone == AssistantSettings().tone
    assert settings.away_minutes == 45


def test_email_pattern_masks_common_address_shapes():
    for email in ["jane.doe@example.com", "first+tag@mail.example.co.uk", "dev_1@sub-domain.example.org"]:
        assert redact(f"Inbox - {email} - Mail") == "Inbox - [email] - Mail"


def test_email_pattern_ignores_text_without_a_domain():
    assert redact("Meeting @ 10:00 - team@work") == "Meeting @ 10:00 - team@work"


def test_email_pattern_masks_retina_file_names_too():
    # Known over-masking: "icon@2x.png" looks like an email. Masking too much is the safe side for privacy.
    assert redact("icon@2x.png") == "[email]"


def test_long_numbers_are_masked_but_years_and_times_are_not():
    assert redact("IBAN DE89 3704 0044 0532 0130 00") == "IBAN DE89 [number]"
    assert redact("Report 2026 - 10:45") == "Report 2026 - 10:45"


def test_integration_guard_refuses_a_database_not_ending_in_test():
    from _pytest.outcomes import Failed

    from conftest import checked_test_database_url

    with pytest.raises(Failed, match="must end in _test"):
        checked_test_database_url("postgresql+psycopg2://me@localhost/cognitive_os")
    assert checked_test_database_url("postgresql+psycopg2://me@localhost/cognitive_os_test").endswith("_test")
