"""
macOS Native Notification Dispatcher for AI Cognitive OS.
Uses AppleScript (osascript) via non-blocking sub-processes to display
slide-in desktop notifications for predicted next workflows.
"""
import subprocess
import time
import logging
from typing import Optional, Dict

logger = logging.getLogger("notifications")

# Cooldown constants to prevent alert fatigue
GLOBAL_COOLDOWN_SECONDS = 45       # At least 45 seconds between any desktop notifications
SAME_SUGGESTION_COOLDOWN = 180     # At least 3 minutes before re-suggesting the exact same app


class NotificationManager:
    """
    Manages proactive desktop notifications with intelligent cooldown and deduplication.
    """
    def __init__(self):
        self._last_global_notify_time: float = 0.0
        self._last_suggestion_time: Dict[str, float] = {}

    def should_notify(self, trigger_app: str, predicted_app: str) -> bool:
        """
        Evaluates whether a notification is permitted based on anti-spam cooldowns.
        """
        now = time.time()
        
        # 1. Global anti-spam cooldown check
        if (now - self._last_global_notify_time) < GLOBAL_COOLDOWN_SECONDS:
            return False

        # 2. Per-suggestion cooldown check
        suggestion_key = f"{trigger_app}->{predicted_app}"
        last_time = self._last_suggestion_time.get(suggestion_key, 0.0)
        if (now - last_time) < SAME_SUGGESTION_COOLDOWN:
            return False

        return True

    def dispatch_suggestion(
        self,
        trigger_app: str,
        predicted_app: str,
        confidence_percent: int,
        sound: str = "Glass",
        show_popup: bool = True
    ) -> bool:
        """
        Dispatches a native macOS slide-in desktop notification asynchronously.
        With show_popup=False the same cooldowns apply, but no pop-up is sent:
        the suggestion is only recorded and shown quietly in the dashboard.
        Returns True if the suggestion went out, False if suppressed by cooldown.
        """
        if not self.should_notify(trigger_app, predicted_app):
            return False

        if not show_popup:
            now = time.time()
            self._last_global_notify_time = now
            self._last_suggestion_time[f"{trigger_app}->{predicted_app}"] = now
            logger.info(f"Quiet suggestion (no pop-up) for {trigger_app} -> {predicted_app} ({confidence_percent}%)")
            return True

        title = "AI Cognitive OS"
        subtitle = f"Workflow Prediction ({confidence_percent}% confidence)"
        message = f"You frequently switch to {predicted_app} after {trigger_app}. Open {predicted_app}?"

        # Sanitize text for AppleScript string literals
        clean_title = title.replace('"', '\\"')
        clean_subtitle = subtitle.replace('"', '\\"')
        clean_message = message.replace('"', '\\"')

        apple_script = (
            f'display notification "{clean_message}" '
            f'with title "{clean_title}" '
            f'subtitle "{clean_subtitle}" '
            f'sound name "{sound}"'
        )

        try:
            # Fire-and-forget asynchronous subprocess so the telemetry loop is not blocked
            subprocess.Popen(
                ["osascript", "-e", apple_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            now = time.time()
            self._last_global_notify_time = now
            self._last_suggestion_time[f"{trigger_app}->{predicted_app}"] = now
            logger.info(f"Dispatched notification for {trigger_app} -> {predicted_app} ({confidence_percent}%)")
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch notification: {e}")
            return False


# Singleton instance for the application daemon
notification_manager = NotificationManager()
