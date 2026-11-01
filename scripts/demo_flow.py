"""
Live Demonstration Script for Hour 6 Workflow Intelligence:
1. Simulates switching to Google Chrome
2. Markov engine predicts: Antigravity IDE (52% confidence)
3. Dispatches native macOS notification
4. Simulates switching to Antigravity IDE (accepted prediction feedback)
5. Live dashboard at http://localhost:5173 updates with the result!
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.pattern_engine import MarkovPatternEngine
from backend.notifications import notification_manager
from backend.models import AIPrediction

def run_demo():
    print("=" * 60)
    print("AI Cognitive OS — Live Prediction & Feedback Simulation")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Step 1: User enters Google Chrome
        current_app = "Google Chrome"
        print(f"\n[EVENT 1] User focuses on '{current_app}'")

        # Step 2: Query Markov Engine for prediction
        pred = MarkovPatternEngine.predict_next(current_app, db)
        if not pred:
            print("No prediction found.")
            return

        print(f"[PREDICTION] Engine predicts user will switch to: '{pred['predicted_app']}' ({pred['confidence_percent']}% confidence)")

        # Step 3: Dispatch macOS desktop notification
        dispatched = notification_manager.dispatch_suggestion(
            trigger_app=pred["trigger_app"],
            predicted_app=pred["predicted_app"],
            confidence_percent=pred["confidence_percent"]
        )
        print(f"[NOTIFICATION] Native desktop notification dispatched: {dispatched}")

        # Step 4: Record prediction as 'suggested'
        rec = MarkovPatternEngine.record_prediction(
            trigger=pred["trigger_app"],
            predicted=pred["predicted_app"],
            status="suggested",
            db=db
        )
        print(f"[DATABASE] Recorded AIPrediction ID {rec.id} with status: 'suggested'")

        # Step 5: Simulate user accepting the suggestion 2 seconds later
        print("\n... User clicks or switches to the suggested app (Antigravity IDE) ...")
        time.sleep(2)

        next_app = pred["predicted_app"] # "Antigravity IDE"
        print(f"[EVENT 2] User switches to '{next_app}'")

        # Evaluate feedback loop
        if rec.suggested_action == next_app:
            rec.status = "accepted"
            db.commit()
            print(f"[FEEDBACK LOOP] Prediction verified! Status updated to: 'accepted' (Habit reinforced!)")
        else:
            rec.status = "ignored"
            db.commit()

        print("\n" + "=" * 60)
        print("Simulation complete! Check http://localhost:5173 to see the updated card.")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    run_demo()
