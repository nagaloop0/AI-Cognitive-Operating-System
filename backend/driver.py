import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.database import engine, Base, SessionLocal
from backend.models import AppActivity, UserPreference, AIPrediction
from backend.tracker import get_tracker
from backend.tracker.input_tracker import InputTracker
from backend.pattern_engine import MarkovPatternEngine
from backend.notifications import notification_manager

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

POLL_INTERVAL = 2          # Check window state every 2 seconds
IDLE_TIMEOUT_POLLS = 10     # 20 seconds of no key/mouse input = idle (shortened for easy testing)
TRAIN_INTERVAL_SWITCHES = 5 # Retrain Markov transitions every 5 app switches

def run_driver():
    print("Starting AI Cognitive OS Driver...")
    print("Local database is connected.")
    
    # Train initial patterns from existing database history
    try:
        init_db = SessionLocal()
        learned = MarkovPatternEngine.train_patterns(init_db)
        if learned:
            print(f"[PATTERNS] Initialized {len(learned)} habit pattern(s) from database history.")
        init_db.close()
    except Exception as e:
        print(f"[PATTERNS INIT ERROR] {e}")

    # Initialize trackers
    os_tracker = get_tracker()
    input_tracker = InputTracker()
    input_tracker.start()
    print("Background input activity listeners started.")
    
    current_activity_id = None
    idle_polls_count = 0
    is_idle = False
    app_switch_count = 0
    pending_prediction_id = None
    
    try:
        while True:
            # 1. Poll the OS for the active window
            active_info = os_tracker.get_active_window()
            
            # 2. Read and reset input counts
            keys, clicks = input_tracker.get_and_reset_counts()
            
            db: Session = SessionLocal()
            now = datetime.now(timezone.utc)
            
            try:
                # Check if user has paused tracking via API / Preference
                pref = db.query(UserPreference).filter(UserPreference.key == "is_tracking_paused").first()
                if pref and pref.value == "true":
                    if current_activity_id:
                        # Close active session
                        active_record = db.query(AppActivity).filter(AppActivity.id == current_activity_id).first()
                        if active_record:
                            active_record.end_time = now
                            start_dt = active_record.start_time.replace(tzinfo=timezone.utc) if active_record.start_time.tzinfo is None else active_record.start_time
                            active_record.duration_seconds = int((now - start_dt).total_seconds())
                            db.commit()
                            current_activity_id = None
                    time.sleep(POLL_INTERVAL)
                    continue

                # Presence detection: check if there was any activity in this tick
                has_input = (keys > 0 or clicks > 0)
                
                if not has_input:
                    idle_polls_count += 1
                else:
                    idle_polls_count = 0
                    if is_idle:
                        print("[RIVER] User returned from idle.")
                        is_idle = False
                
                # Check if user crossed the idle threshold
                if idle_polls_count >= IDLE_TIMEOUT_POLLS and not is_idle:
                    print(f"[DRIVER] User went idle (no activity for {IDLE_TIMEOUT_POLLS * POLL_INTERVAL} seconds).")
                    is_idle = True
                    # Close the current active window session so we don't inflate screen time
                    if current_activity_id:
                        activity = db.query(AppActivity).filter(AppActivity.id == current_activity_id).first()
                        if activity and not activity.end_time:
                            activity.end_time = now
                            start_dt = activity.start_time.replace(tzinfo=timezone.utc) if activity.start_time.tzinfo is None else activity.start_time
                            activity.duration_seconds = int((now - start_dt).total_seconds())
                            db.commit()
                            current_activity_id = None
                
                # If user is active and we have window metadata
                if active_info and not is_idle:
                    app_name, window_title = active_info
                    
                    # Fetch active record
                    active_record = None
                    if current_activity_id:
                        active_record = db.query(AppActivity).filter(AppActivity.id == current_activity_id).first()
                    
                    # Case A: No active record, or application/window title changed
                    if not active_record or active_record.app_name != app_name or active_record.window_title != window_title:
                        is_app_switch = bool(active_record and active_record.app_name != app_name)

                        # Close the old record if it exists
                        if active_record:
                            active_record.end_time = now
                            start_dt = active_record.start_time.replace(tzinfo=timezone.utc) if active_record.start_time.tzinfo is None else active_record.start_time
                            active_record.duration_seconds = int((now - start_dt).total_seconds())
                            db.commit()
                        
                        # Open a new activity record
                        new_record = AppActivity(
                            app_name=app_name,
                            window_title=window_title,
                            keystroke_count=keys,
                            mouse_click_count=clicks,
                            start_time=now
                        )
                        db.add(new_record)
                        db.commit()
                        db.refresh(new_record)
                        current_activity_id = new_record.id
                        print(f"[DRIVER] Active Window: {app_name} | Title: {window_title} | Keys: {keys} | Clicks: {clicks}")

                        # Trigger prediction & feedback loop on application switches
                        if is_app_switch:
                            # 1. Evaluate previous prediction feedback
                            if pending_prediction_id:
                                pending = db.query(AIPrediction).filter(AIPrediction.id == pending_prediction_id).first()
                                if pending and pending.status == "suggested":
                                    if pending.suggested_action == app_name:
                                        pending.status = "accepted"
                                        print(f"[FEEDBACK] Prediction accepted! User opened suggested app: {app_name}")
                                    else:
                                        pending.status = "ignored"
                                    db.commit()
                                pending_prediction_id = None

                            # 2. Increment switch counter and periodically retrain patterns
                            app_switch_count += 1
                            if app_switch_count % TRAIN_INTERVAL_SWITCHES == 0:
                                learned = MarkovPatternEngine.train_patterns(db)
                                if learned:
                                    print(f"[PATTERNS] Retrained Markov transitions: {len(learned)} active habit(s).")

                            # 3. Query prediction for newly focused application
                            prediction = MarkovPatternEngine.predict_next(app_name, db)
                            if prediction:
                                print(f"[PREDICTION] Evaluated '{app_name}' ➔ Top candidate: '{prediction['predicted_app']}' ({prediction['confidence_percent']}% confidence)")
                                # Desktop pop-ups are off unless the user turns them on (they interrupt more than they help)
                                popup_pref = db.query(UserPreference).filter(UserPreference.key == "desktop_notifications_enabled").first()
                                show_popup = popup_pref is not None and popup_pref.value == "true"
                                dispatched = notification_manager.dispatch_suggestion(
                                    trigger_app=prediction["trigger_app"],
                                    predicted_app=prediction["predicted_app"],
                                    confidence_percent=prediction["confidence_percent"],
                                    show_popup=show_popup
                                )
                                if dispatched:
                                    pred_record = MarkovPatternEngine.record_prediction(
                                        trigger=prediction["trigger_app"],
                                        predicted=prediction["predicted_app"],
                                        status="suggested",
                                        db=db
                                    )
                                    pending_prediction_id = pred_record.id
                                    if show_popup:
                                        print(f"[NOTIFICATION] 🔔 macOS desktop notification dispatched for '{prediction['predicted_app']}'!")
                                    else:
                                        print(f"[SUGGESTION] Recorded quietly for the dashboard (desktop pop-ups are off).")
                                else:
                                    print(f"[NOTIFICATION] Suppressed by anti-spam cooldown (must wait 45s between desktop alerts).")
                            else:
                                print(f"[PREDICTION] No habit pattern found for '{app_name}' with >= 50% confidence.")
                    
                    # Case B: Still in the same window, accumulate data
                    else:
                        active_record.keystroke_count += keys
                        active_record.mouse_click_count += clicks
                        if keys > 0 or clicks > 0:
                            # what are we printing the keys are we storing them all here ..?
                            print(f"[DRIVER] Activity in {app_name} | +{keys} keys | +{clicks} clicks (Total: {active_record.keystroke_count} keys, {active_record.mouse_click_count} clicks)")
                        start_dt = active_record.start_time.replace(tzinfo=timezone.utc) if active_record.start_time.tzinfo is None else active_record.start_time
                        active_record.duration_seconds = int((now - start_dt).total_seconds())
                        db.commit()
                
                # If window detection fails (e.g., lock screen, screensaver), close the current active record
                elif not active_info and current_activity_id:
                    active_record = db.query(AppActivity).filter(AppActivity.id == current_activity_id).first()
                    if active_record:
                        active_record.end_time = now
                        start_dt = active_record.start_time.replace(tzinfo=timezone.utc) if active_record.start_time.tzinfo is None else active_record.start_time
                        active_record.duration_seconds = int((now - start_dt).total_seconds())
                        db.commit()
                        current_activity_id = None
            
            except Exception as e:
                print(f"[DRIVER ERROR] {e}")
                db.rollback()
            finally:
                db.close()
                
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping background driver...")
    finally:
        input_tracker.stop()
        print("Listeners stopped. driver shut down.")

if __name__ == "__main__":
    run_driver()
