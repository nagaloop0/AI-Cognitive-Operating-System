from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from backend.database import get_db, engine, Base
from backend.models import AppActivity, UserPreference, HabitPattern, AIPrediction
from backend.pattern_engine import MarkovPatternEngine
from backend.schemas import (
    OverallSummary,
    AppSummary,
    TimelineItem,
    PreferenceStatus,
    NotificationStatus,
    MessageResponse,
    DashboardData,
    HabitPatternItem,
    PredictionItem
)

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Cognitive OS API",
    description="Local REST API for activity statistics, workflow patterns, and user privacy control.",
    version="1.0.0"
)

# Enable CORS so Vue 3 frontend dashboard (Vite / local dev) can connect seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=MessageResponse)
def root():
    """Health check endpoint."""
    return {"message": "AI Cognitive OS API is online and running."}

@app.get("/api/stats/summary", response_model=OverallSummary)
def get_overall_summary(db: Session = Depends(get_db)):
    """Returns overall total duration, total keystrokes, total mouse clicks, and session counts."""
    total_duration = db.query(func.coalesce(func.sum(AppActivity.duration_seconds), 0)).scalar()
    total_keystrokes = db.query(func.coalesce(func.sum(AppActivity.keystroke_count), 0)).scalar()
    total_clicks = db.query(func.coalesce(func.sum(AppActivity.mouse_click_count), 0)).scalar()
    total_sessions = db.query(func.count(AppActivity.id)).scalar()

    return OverallSummary(
        total_duration_seconds=int(total_duration),
        total_keystrokes=int(total_keystrokes),
        total_clicks=int(total_clicks),
        total_sessions=int(total_sessions)
    )

@app.get("/api/stats/apps", response_model=list[AppSummary])
def get_app_stats(db: Session = Depends(get_db)):
    """Returns statistics aggregated by application name, sorted by time spent descending."""
    results = (
        db.query(
            AppActivity.app_name,
            func.coalesce(func.sum(AppActivity.duration_seconds), 0).label("total_duration"),
            func.coalesce(func.sum(AppActivity.keystroke_count), 0).label("total_keystrokes"),
            func.coalesce(func.sum(AppActivity.mouse_click_count), 0).label("total_clicks"),
            func.count(AppActivity.id).label("session_count")
        )
        .group_by(AppActivity.app_name)
        .order_by(func.sum(AppActivity.duration_seconds).desc())
        .all()
    )

    return [
        AppSummary(
            app_name=row.app_name,
            total_duration_seconds=int(row.total_duration),
            total_keystrokes=int(row.total_keystrokes),
            total_clicks=int(row.total_clicks),
            session_count=int(row.session_count)
        )
        for row in results
    ]

@app.get("/api/stats/timeline", response_model=list[TimelineItem])
def get_timeline(limit: int = 20, db: Session = Depends(get_db)):
    """Returns the most recent activity window sessions ordered chronologically."""
    sessions = (
        db.query(AppActivity)
        .order_by(AppActivity.id.desc())
        .limit(limit)
        .all()
    )
    return sessions

@app.get("/api/stats/dashboard", response_model=DashboardData)
def get_dashboard_data(limit: int = 15, db: Session = Depends(get_db)):
    """Bundled high-performance endpoint returning summary, apps, timeline, and preference in a single query."""
    # Summary
    total_duration = db.query(func.coalesce(func.sum(AppActivity.duration_seconds), 0)).scalar()
    total_keystrokes = db.query(func.coalesce(func.sum(AppActivity.keystroke_count), 0)).scalar()
    total_clicks = db.query(func.coalesce(func.sum(AppActivity.mouse_click_count), 0)).scalar()
    total_sessions = db.query(func.count(AppActivity.id)).scalar()

    summary = OverallSummary(
        total_duration_seconds=int(total_duration),
        total_keystrokes=int(total_keystrokes),
        total_clicks=int(total_clicks),
        total_sessions=int(total_sessions)
    )

    # Apps
    app_results = (
        db.query(
            AppActivity.app_name,
            func.coalesce(func.sum(AppActivity.duration_seconds), 0).label("total_duration"),
            func.coalesce(func.sum(AppActivity.keystroke_count), 0).label("total_keystrokes"),
            func.coalesce(func.sum(AppActivity.mouse_click_count), 0).label("total_clicks"),
            func.count(AppActivity.id).label("session_count")
        )
        .group_by(AppActivity.app_name)
        .order_by(func.sum(AppActivity.duration_seconds).desc())
        .all()
    )
    apps = [
        AppSummary(
            app_name=row.app_name,
            total_duration_seconds=int(row.total_duration),
            total_keystrokes=int(row.total_keystrokes),
            total_clicks=int(row.total_clicks),
            session_count=int(row.session_count)
        )
        for row in app_results
    ]

    # Timeline
    timeline = (
        db.query(AppActivity)
        .order_by(AppActivity.id.desc())
        .limit(limit)
        .all()
    )

    # Preference
    pref = db.query(UserPreference).filter(UserPreference.key == "is_tracking_paused").first()
    is_paused = (pref.value == "true") if pref else False

    # Learned Habit Patterns & Recent Proactive Predictions
    patterns = (
        db.query(HabitPattern)
        .order_by(HabitPattern.confidence.desc(), HabitPattern.occurrence_count.desc())
        .limit(10)
        .all()
    )
    recent_predictions = (
        db.query(AIPrediction)
        .order_by(AIPrediction.id.desc())
        .limit(10)
        .all()
    )

    return DashboardData(
        summary=summary,
        apps=apps,
        timeline=timeline,
        preference=PreferenceStatus(is_tracking_paused=is_paused),
        patterns=patterns,
        recent_predictions=recent_predictions
    )

@app.get("/api/patterns/habits", response_model=list[HabitPatternItem])
def get_habit_patterns(db: Session = Depends(get_db)):
    """Returns all learned statistical transition patterns above confidence threshold."""
    return (
        db.query(HabitPattern)
        .order_by(HabitPattern.confidence.desc(), HabitPattern.occurrence_count.desc())
        .all()
    )

@app.get("/api/patterns/predictions", response_model=list[PredictionItem])
def get_predictions(limit: int = 15, db: Session = Depends(get_db)):
    """Returns recent workflow predictions and their user feedback status."""
    return (
        db.query(AIPrediction)
        .order_by(AIPrediction.id.desc())
        .limit(limit)
        .all()
    )

@app.post("/api/patterns/retrain", response_model=MessageResponse)
def retrain_patterns(db: Session = Depends(get_db)):
    """Manually triggers Markov chain transition analysis on historical telemetry."""
    learned = MarkovPatternEngine.train_patterns(db)
    return {"message": f"Successfully analyzed transitions and trained {len(learned)} habit pattern(s)."}

@app.get("/api/control/status", response_model=PreferenceStatus)
def get_tracking_status(db: Session = Depends(get_db)):
    """Returns current tracking pause status."""
    pref = db.query(UserPreference).filter(UserPreference.key == "is_tracking_paused").first()
    is_paused = (pref.value == "true") if pref else False
    return PreferenceStatus(is_tracking_paused=is_paused)

@app.post("/api/control/toggle", response_model=PreferenceStatus)
def toggle_tracking_status(db: Session = Depends(get_db)):
    """Toggles background driver tracking between active and paused."""
    pref = db.query(UserPreference).filter(UserPreference.key == "is_tracking_paused").first()
    if not pref:
        pref = UserPreference(key="is_tracking_paused", value="true")
        db.add(pref)
    else:
        pref.value = "false" if pref.value == "true" else "true"
    db.commit()
    db.refresh(pref)
    return PreferenceStatus(is_tracking_paused=(pref.value == "true"))

@app.get("/api/control/notifications", response_model=NotificationStatus)
def get_notification_status(db: Session = Depends(get_db)):
    """Returns whether desktop pop-ups are on. Off by default: suggestions show only in the dashboard."""
    pref = db.query(UserPreference).filter(UserPreference.key == "desktop_notifications_enabled").first()
    return NotificationStatus(desktop_notifications_enabled=(pref is not None and pref.value == "true"))

@app.post("/api/control/notifications/toggle", response_model=NotificationStatus)
def toggle_notifications(db: Session = Depends(get_db)):
    """Turns desktop pop-ups on or off."""
    pref = db.query(UserPreference).filter(UserPreference.key == "desktop_notifications_enabled").first()
    if not pref:
        pref = UserPreference(key="desktop_notifications_enabled", value="true")
        db.add(pref)
    else:
        pref.value = "false" if pref.value == "true" else "true"
    db.commit()
    db.refresh(pref)
    return NotificationStatus(desktop_notifications_enabled=(pref.value == "true"))

@app.post("/api/control/clear-history", response_model=MessageResponse)
def clear_activity_history(db: Session = Depends(get_db)):
    """Permanently deletes all recorded app activities (User Privacy Rule #4)."""
    deleted_count = db.query(AppActivity).delete()
    db.commit()
    return {"message": f"Successfully deleted {deleted_count} activity records."}
