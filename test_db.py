import os
from backend.database import engine, Base, SessionLocal
from backend.models import AppActivity
from datetime import datetime, timezone

def test_database():
    print("1. Creating database tables in ~/.cognitive_os/activity.db ...")
    # This will create the .db file and tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    print("2. Inserting a test record...")
    db = SessionLocal()
    try:
        new_activity = AppActivity(
            app_name="TestApp",
            window_title="Test Window - Hello World",
            keystroke_count=42, # Mock count
            mouse_click_count=5
        )
        db.add(new_activity)
        db.commit()
        db.refresh(new_activity)
        print(f"   Successfully inserted record with ID: {new_activity.id}")
        
        print("3. Querying the record...")
        record = db.query(AppActivity).filter(AppActivity.id == new_activity.id).first()
        if record:
            print(f"   Found record: App={record.app_name}, Keystrokes={record.keystroke_count}")
        else:
            print("   Failed to find record!")
            
    except Exception as e:
        print(f"Error during DB operations: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
