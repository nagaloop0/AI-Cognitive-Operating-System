"""
Integration Test for Hour 6: Markov Pattern Engine & macOS Notifications.
Runs standalone without starting the background driver daemon.
"""
import os
import sys
import time

# Ensure project root is in sys.path when executed directly as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.pattern_engine import MarkovPatternEngine
from backend.notifications import notification_manager
from backend.models import HabitPattern, AppActivity

def run_tests():
    print("=" * 60)
    print("AI Cognitive OS — Hour 6 Pattern & Notification Verification")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Step 1: Check existing activity telemetry count
        total_activities = db.query(AppActivity).count()
        print(f"\n[1/4] Database Check: Found {total_activities} historical activity records.")

        # Step 2: Train Markov transition engine
        print("\n[2/4] Running Markov Chain Transition Analysis...")
        learned = MarkovPatternEngine.train_patterns(db)
        print(f"      Learned {len(learned)} habit sequence(s) from history.")
        for p in learned:
            print(f"      * {p['trigger']} -> {p['predicted']} ({p['count']}x observed, {int(p['confidence']*100)}% confidence)")

        # Step 3: Test prediction lookup
        all_habits = db.query(HabitPattern).all()
        if all_habits:
            sample_trigger = all_habits[0].trigger_sequence
            pred = MarkovPatternEngine.predict_next(sample_trigger, db)
            print(f"\n[3/4] Prediction Test for '{sample_trigger}':")
            print(f"      Top Suggested Next App: {pred['predicted_app']} ({pred['confidence_percent']}% confidence)")
        else:
            print("\n[3/4] Prediction Test: Need at least 2 consecutive app switch activities in DB to predict.")

        # Step 4: Dispatch a live macOS test notification
        print("\n[4/4] Testing macOS Desktop Notification Dispatcher...")
        success = notification_manager.dispatch_suggestion(
            trigger_app="Test Runner",
            predicted_app="AI Cognitive OS",
            confidence_percent=95,
            sound="Glass"
        )
        if success:
            print("      SUCCESS: Slide-in notification dispatched to macOS! Check your top-right screen.")
        else:
            print("      Suppressed by cooldown timer.")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Hour 6 Verification Complete!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
