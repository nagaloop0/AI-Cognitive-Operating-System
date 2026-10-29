"""
Markov Chain Statistical Pattern Engine for AI Cognitive OS.
Analyzes historical application transition sequences to predict the user's
next likely action based on conditional probabilities: P(App_{t+1} = B | App_t = A).
"""
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.models import AppActivity, HabitPattern, AIPrediction

logger = logging.getLogger("pattern_engine")

# Hyperparameters for statistical validity
MIN_OCCURRENCES = 2              # Need at least 2 occurrences to establish a pattern
CONFIDENCE_THRESHOLD = 0.50      # Minimum conditional probability (50%) to trigger suggestion
MAX_SESSION_GAP_SECONDS = 300    # If idle gap between apps > 5 minutes, do not link as consecutive workflow


class MarkovPatternEngine:
    """
    Computes first-order Discrete Markov Chain transitions from user telemetry.
    Transition Matrix: P(B | A) = Count(A -> B) / Total_Transitions(A)
    """

    @staticmethod
    def train_patterns(db: Session) -> List[Dict[str, Any]]:
        """
        Scans all chronological AppActivity records, computes transition frequencies,
        calculates conditional confidence scores, and updates the HabitPattern table.
        """
        # 1. Fetch activities ordered by start_time ascending
        activities = (
            db.query(AppActivity)
            .order_by(AppActivity.start_time.asc())
            .all()
        )

        if len(activities) < 2:
            return []

        # 2. Extract consecutive transitions across app switches
        # transitions[source_app][target_app] = count
        transition_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        total_transitions_from: Dict[str, int] = defaultdict(int)

        prev_activity: Optional[AppActivity] = None

        for curr in activities:
            if not curr.app_name:
                continue

            if prev_activity is not None:
                # Same app continued in different window -> not an app switch
                if prev_activity.app_name != curr.app_name:
                    # Check if the time gap is within workflow threshold
                    # Handle timezone-aware or naive datetimes gracefully
                    prev_end = prev_activity.end_time or prev_activity.start_time
                    curr_start = curr.start_time
                    
                    if prev_end and curr_start:
                        # Normalize timezones for delta calculation
                        t1 = prev_end.replace(tzinfo=timezone.utc) if prev_end.tzinfo is None else prev_end
                        t2 = curr_start.replace(tzinfo=timezone.utc) if curr_start.tzinfo is None else curr_start
                        gap = abs((t2 - t1).total_seconds())

                        if gap <= MAX_SESSION_GAP_SECONDS:
                            src = prev_activity.app_name
                            dst = curr.app_name
                            transition_counts[src][dst] += 1
                            total_transitions_from[src] += 1

            prev_activity = curr

        # 3. Compute probabilities and sync with HabitPattern table
        learned_patterns = []
        now = datetime.now(timezone.utc)

        for src_app, targets in transition_counts.items():
            total = total_transitions_from[src_app]
            if total == 0:
                continue

            for dst_app, count in targets.items():
                confidence = round(count / total, 3)

                # Filter out one-off noise below threshold
                if count >= MIN_OCCURRENCES and confidence >= CONFIDENCE_THRESHOLD:
                    # Check if habit pattern already exists
                    habit = (
                        db.query(HabitPattern)
                        .filter(
                            HabitPattern.trigger_sequence == src_app,
                            HabitPattern.predicted_action == dst_app
                        )
                        .first()
                    )

                    if habit:
                        habit.occurrence_count = count
                        habit.confidence = confidence
                        habit.last_triggered = now
                    else:
                        habit = HabitPattern(
                            trigger_sequence=src_app,
                            predicted_action=dst_app,
                            occurrence_count=count,
                            confidence=confidence,
                            last_triggered=now
                        )
                        db.add(habit)

                    learned_patterns.append({
                        "trigger": src_app,
                        "predicted": dst_app,
                        "count": count,
                        "confidence": confidence
                    })

        db.commit()
        return learned_patterns

    @staticmethod
    def predict_next(current_app: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Given the current active application, consults the learned habit patterns
        and returns the highest-confidence next application prediction (if above threshold).
        """
        if not current_app:
            return None

        # Fetch candidate patterns for this trigger app, sorted by highest confidence and occurrence count
        top_pattern = (
            db.query(HabitPattern)
            .filter(
                HabitPattern.trigger_sequence == current_app,
                HabitPattern.confidence >= CONFIDENCE_THRESHOLD,
                HabitPattern.occurrence_count >= MIN_OCCURRENCES
            )
            .order_by(
                HabitPattern.confidence.desc(),
                HabitPattern.occurrence_count.desc()
            )
            .first()
        )

        if not top_pattern:
            return None

        return {
            "trigger_app": top_pattern.trigger_sequence,
            "predicted_app": top_pattern.predicted_action,
            "confidence": top_pattern.confidence,
            "occurrence_count": top_pattern.occurrence_count,
            "confidence_percent": int(top_pattern.confidence * 100)
        }

    @staticmethod
    def record_prediction(
        trigger: str,
        predicted: str,
        status: str,
        db: Session
    ) -> AIPrediction:
        """
        Logs a generated prediction into the AIPrediction table to build the AI feedback loop.
        Status: 'suggested', 'accepted', 'ignored'
        """
        pred = AIPrediction(
            trigger_sequence=trigger,
            suggested_action=predicted,
            status=status,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)
        return pred
