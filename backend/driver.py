"""
Background tracker: every 2 seconds it records the active window, detects idle time,
learns app habits and lets the assistant speak at the right moment.

Run: venv/bin/python -m backend.driver
"""
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.assistant import end_of_day, sent_on, welcome_back
from backend.database import SessionLocal, init_db
from backend.llm_client import LLMClient
from backend.models import AIPrediction, AppActivity, UserPreference
from backend.notifications import notification_manager
from backend.pattern_engine import MarkovPatternEngine
from backend.privacy import title_for_storage
from backend.settings import AssistantSettings, load_settings
from backend.timeutil import as_utc, local_tz
from backend.timing import idle_threshold_seconds, is_end_of_day_due, is_welcome_back

logger = logging.getLogger("driver")

POLL_INTERVAL = 2               # check the active window every 2 seconds
TRAIN_INTERVAL_SWITCHES = 5     # retrain Markov transitions every 5 app switches
SETTINGS_REFRESH_SECONDS = 30   # pick up settings changed in the dashboard
END_OF_DAY_RETRY = timedelta(minutes=10)


class ActivityDriver:
    def __init__(self, session_factory=SessionLocal, llm_factory=LLMClient, run_in_background: bool = True):
        self.session_factory = session_factory
        self.llm_factory = llm_factory
        self.run_in_background = run_in_background

        self.current_activity_id: int | None = None
        self.last_input_at: datetime | None = None
        self.is_idle = False
        self.app_switch_count = 0
        self.pending_prediction_id: int | None = None
        self.settings = AssistantSettings()
        self._settings_loaded_at: datetime | None = None
        self._end_of_day_busy = threading.Event()
        self._end_of_day_done_for: date | None = None
        self._end_of_day_retry_at: datetime | None = None

    # ---- one poll -------------------------------------------------------------------------------

    def tick(self, now: datetime, active_window: tuple[str, str] | None, keys: int, clicks: int) -> None:
        db = self.session_factory()
        try:
            self._refresh_settings(db, now)
            if self._is_paused(db):
                self._close_current(db, now)
                return

            app_name = title = None
            if active_window:
                app_name, raw_title = active_window
                title = title_for_storage(app_name, raw_title, self.settings.private_apps,
                                          self.settings.private_title_words)

            self._update_presence(db, now, keys > 0 or clicks > 0, app_name, title)
            if active_window and not self.is_idle:
                self._record_window(db, now, app_name, title, keys, clicks)
            elif not active_window:
                # Lock screen or screensaver: no window can be read
                self._close_current(db, now)
            self._check_end_of_day(now)
        except Exception as e:
            logger.exception("Driver tick failed")
            print(f"[DRIVER ERROR] {e}")
            db.rollback()
        finally:
            db.close()

    # ---- presence ------------------------------------------------------------------------------

    def _update_presence(self, db: Session, now: datetime, has_input: bool, app_name, title) -> None:
        if self.last_input_at is None:
            self.last_input_at = now  # starting the driver counts as being present

        if has_input:
            if self.is_idle:
                away_seconds = (now - self.last_input_at).total_seconds()
                self.is_idle = False
                print(f"[DRIVER] User returned after {int(away_seconds)} s.")
                if is_welcome_back(away_seconds, self.settings):
                    message = welcome_back(db, self.last_input_at, away_seconds, self.settings)
                    print(f"[ASSISTANT] {message.title} {message.body}")
            self.last_input_at = now
            return

        idle_after = idle_threshold_seconds(app_name, title, self.settings)
        if not self.is_idle and (now - self.last_input_at).total_seconds() >= idle_after:
            self.is_idle = True
            print(f"[DRIVER] User went idle (no input for {idle_after} s).")
            # Screen time ends at the last input, so idle minutes are not counted as work
            self._close_current(db, self.last_input_at)

    # ---- activity records ----------------------------------------------------------------------

    def _record_window(self, db: Session, now: datetime, app_name: str, title: str, keys: int, clicks: int) -> None:
        current = db.get(AppActivity, self.current_activity_id) if self.current_activity_id else None

        if current and current.app_name == app_name and current.window_title == title:
            current.keystroke_count += keys
            current.mouse_click_count += clicks
            current.duration_seconds = self._seconds_since(current.start_time, now)
            db.commit()
            return

        is_app_switch = bool(current and current.app_name != app_name)
        self._close_current(db, now)
        record = AppActivity(app_name=app_name, window_title=title, keystroke_count=keys,
                             mouse_click_count=clicks, start_time=now)
        db.add(record)
        db.commit()
        self.current_activity_id = record.id
        print(f"[DRIVER] Active window: {app_name} | {title}")

        if is_app_switch:
            self._on_app_switch(db, app_name)

    def _close_current(self, db: Session, end: datetime) -> None:
        if not self.current_activity_id:
            return
        record = db.get(AppActivity, self.current_activity_id)
        if record and not record.end_time:
            end = max(end, as_utc(record.start_time))
            record.end_time = end
            record.duration_seconds = self._seconds_since(record.start_time, end)
            db.commit()
        self.current_activity_id = None

    @staticmethod
    def _seconds_since(start: datetime, now: datetime) -> int:
        return int((now - as_utc(start)).total_seconds())

    # ---- habits and predictions ----------------------------------------------------------------

    def _on_app_switch(self, db: Session, app_name: str) -> None:
        # 1. Feedback on the previous prediction
        if self.pending_prediction_id:
            pending = db.get(AIPrediction, self.pending_prediction_id)
            if pending and pending.status == "suggested":
                pending.status = "accepted" if pending.suggested_action == app_name else "ignored"
                db.commit()
            self.pending_prediction_id = None

        # 2. Retrain every few switches
        self.app_switch_count += 1
        if self.app_switch_count % TRAIN_INTERVAL_SWITCHES == 0:
            learned = MarkovPatternEngine.train_patterns(db)
            print(f"[PATTERNS] Retrained: {len(learned)} habit(s).")

        # 3. Predict the next app; pop-ups only if the user turned them on
        prediction = MarkovPatternEngine.predict_next(app_name, db)
        if not prediction:
            return
        popup_pref = db.query(UserPreference).filter(UserPreference.key == "desktop_notifications_enabled").first()
        show_popup = popup_pref is not None and popup_pref.value == "true"
        dispatched = notification_manager.dispatch_suggestion(
            trigger_app=prediction["trigger_app"], predicted_app=prediction["predicted_app"],
            confidence_percent=prediction["confidence_percent"], show_popup=show_popup)
        if dispatched:
            record = MarkovPatternEngine.record_prediction(prediction["trigger_app"], prediction["predicted_app"],
                                                           "suggested", db)
            self.pending_prediction_id = record.id
            print(f"[PREDICTION] {app_name} -> {prediction['predicted_app']} ({prediction['confidence_percent']}%)")

    # ---- end of day ----------------------------------------------------------------------------

    def _check_end_of_day(self, now: datetime) -> None:
        if self._end_of_day_busy.is_set() or (self._end_of_day_retry_at and now < self._end_of_day_retry_at):
            return
        now_local = now.astimezone(local_tz())
        seconds_since_input = (now - self.last_input_at).total_seconds() if self.last_input_at else 0
        done_today = self._end_of_day_done_for == now_local.date()
        if not is_end_of_day_due(now_local, seconds_since_input, self.settings, already_sent_today=done_today):
            return
        self._end_of_day_busy.set()
        if self.run_in_background:
            # The model takes seconds: never block the 2-second tracking loop
            threading.Thread(target=self._send_end_of_day, args=(now_local.date(), now), daemon=True).start()
        else:
            self._send_end_of_day(now_local.date(), now)

    def _send_end_of_day(self, day, now: datetime) -> None:
        db = self.session_factory()
        try:
            if not sent_on(db, "end_of_day", day):  # also covers a driver restart on the same day
                message = end_of_day(db, self.llm_factory(), day)
                print(f"[ASSISTANT] End of day: {message.title}")
            self._end_of_day_done_for = day
        except Exception:
            logger.exception("End-of-day summary failed")
            self._end_of_day_retry_at = now + END_OF_DAY_RETRY
        finally:
            db.close()
            self._end_of_day_busy.clear()

    # ---- settings and pause --------------------------------------------------------------------

    def _refresh_settings(self, db: Session, now: datetime) -> None:
        if self._settings_loaded_at and (now - self._settings_loaded_at).total_seconds() < SETTINGS_REFRESH_SECONDS:
            return
        self.settings = load_settings(db)
        self._settings_loaded_at = now

    @staticmethod
    def _is_paused(db: Session) -> bool:
        pref = db.query(UserPreference).filter(UserPreference.key == "is_tracking_paused").first()
        return pref is not None and pref.value == "true"


def run_driver() -> None:
    # Imported here: the macOS trackers need Quartz/pynput, which tests and CI do not have
    from backend.tracker import get_tracker
    from backend.tracker.input_tracker import InputTracker

    print("Starting AI Cognitive OS Driver...")
    init_db()
    db = SessionLocal()
    try:
        learned = MarkovPatternEngine.train_patterns(db)
        print(f"[PATTERNS] Initialized {len(learned)} habit pattern(s) from history.")
    finally:
        db.close()

    os_tracker = get_tracker()
    input_tracker = InputTracker()
    input_tracker.start()
    driver = ActivityDriver()
    print("Tracking started. Press Ctrl+C to stop.")
    try:
        while True:
            active_window = os_tracker.get_active_window()
            keys, clicks = input_tracker.get_and_reset_counts()
            driver.tick(datetime.now(timezone.utc), active_window, keys, clicks)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopping background driver...")
    finally:
        input_tracker.stop()
        print("Listeners stopped. Driver shut down.")


if __name__ == "__main__":
    run_driver()
