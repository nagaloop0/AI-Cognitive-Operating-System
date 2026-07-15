import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.database import engine, Base, SessionLocal
from backend.models import AppActivity
from backend.tracker import get_tracker
from backend.tracker.input_tracker import InputTracker

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

POLL_INTERVAL = 2          # Check window state every 2 seconds
IDLE_TIMEOUT_POLLS = 10     # 20 seconds of no key/mouse input = idle (shortened for easy testing)

def run_daemon():
    print("Starting AI Cognitive OS Daemon...")
    print("Local database is connected.")
    
    # Initialize trackers
    os_tracker = get_tracker()
    input_tracker = InputTracker()
    input_tracker.start()
    print("Background input activity listeners started.")
    
    current_activity_id = None
    idle_polls_count = 0
    is_idle = False
    
    try:
        while True:
            # 1. Poll the OS for the active window
            active_info = os_tracker.get_active_window()
            
            # 2. Read and reset input counts
            keys, clicks = input_tracker.get_and_reset_counts()
            
            db: Session = SessionLocal()
            # Convert UTC datetime to offset-naive so it can be safely compared with SQLite datetime columns
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            try:
                # Presence detection: check if there was any activity in this tick
                has_input = (keys > 0 or clicks > 0)
                
                if not has_input:
                    idle_polls_count += 1
                else:
                    idle_polls_count = 0
                    if is_idle:
                        print("[DAEMON] User returned from idle.")
                        is_idle = False
                
                # Check if user crossed the idle threshold
                if idle_polls_count >= IDLE_TIMEOUT_POLLS and not is_idle:
                    print(f"[DAEMON] User went idle (no activity for {IDLE_TIMEOUT_POLLS * POLL_INTERVAL} seconds).")
                    is_idle = True
                    # Close the current active window session so we don't inflate screen time
                    if current_activity_id:
                        activity = db.query(AppActivity).filter(AppActivity.id == current_activity_id).first()
                        if activity and not activity.end_time:
                            activity.end_time = now
                            activity.duration_seconds = int((now - activity.start_time).total_seconds())
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
                        # Close the old record if it exists
                        if active_record:
                            active_record.end_time = now
                            active_record.duration_seconds = int((now - active_record.start_time).total_seconds())
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
                        print(f"[DAEMON] Active Window: {app_name} | Title: {window_title}")
                    
                    # Case B: Still in the same window, accumulate data
                    else:
                        active_record.keystroke_count += keys
                        active_record.mouse_click_count += clicks
                        active_record.duration_seconds = int((now - active_record.start_time).total_seconds())
                        db.commit()
                
                # If window detection fails (e.g., lock screen, screensaver), close the current active record
                elif not active_info and current_activity_id:
                    active_record = db.query(AppActivity).filter(AppActivity.id == current_activity_id).first()
                    if active_record:
                        active_record.end_time = now
                        active_record.duration_seconds = int((now - active_record.start_time).total_seconds())
                        db.commit()
                        current_activity_id = None
            
            except Exception as e:
                print(f"[DAEMON ERROR] {e}")
                db.rollback()
            finally:
                db.close()
                
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping background daemon...")
    finally:
        input_tracker.stop()
        print("Listeners stopped. Daemon shut down.")

if __name__ == "__main__":
    run_daemon()
