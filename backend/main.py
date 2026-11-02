import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from backend.database import get_db, init_db
from backend.models import (
    AppActivity, UserPreference, HabitPattern, AIPrediction,
    DailySummary, AssistantMessage, TitleCategory, TitleEmbedding, Task,
)
from backend.routes import assistant, categories, insights, settings, summary
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist (on server start, not on import, so tests never touch the real database)
    init_db()
    yield

app = FastAPI(
    title="AI Cognitive OS API",
    description="Local REST API for activity statistics, workflow patterns, and user privacy control.",
    version="1.0.0",
    lifespan=lifespan
)

# Only the local Vue dashboard may call this API from a browser (comma-separated list in .env)
# TODO: when the dashboard is packaged as a desktop app (Tauri / Electron), its address changes:
#       add the new origin to ALLOWED_ORIGINS in .env and .env.example (no code change needed).
load_dotenv()
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hosts where the API may trust its own pages (/docs). Keep this to loopback names only.
TRUSTED_LOCAL_HOSTS = set(os.getenv("TRUSTED_LOCAL_HOSTS", "localhost,127.0.0.1").split(","))


def is_allowed_origin(origin: str, host: str) -> bool:
    """The dashboard origins from .env, plus the API's own pages (/docs) when served on localhost.
    Same-origin is only trusted on localhost: with DNS rebinding an attacker's domain can point at
    127.0.0.1, and then its Origin and Host would match too."""
    if origin in ALLOWED_ORIGINS:
        return True
    hostname = host.rsplit(":", 1)[0]
    return hostname in TRUSTED_LOCAL_HOSTS and origin in (f"http://{host}", f"https://{host}")


@app.middleware("http")
async def block_other_websites(request: Request, call_next):
    """Rejects browser requests from any other website.
    CORS alone only hides the response: a simple POST (e.g. clear-history) would still run."""
    origin = request.headers.get("origin")
    if origin and not is_allowed_origin(origin, request.headers.get("host", "")):
        return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
    return await call_next(request)

app.include_router(summary.router)
app.include_router(categories.router)
app.include_router(assistant.router)
app.include_router(settings.router)
app.include_router(insights.router)

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
    """Permanently deletes all recorded activities and everything learned from them (User Privacy Rule #4).
    Settings are kept: they are choices, not activity data."""
    deleted_count = db.query(AppActivity).delete()
    habit_count = db.query(HabitPattern).delete()
    prediction_count = db.query(AIPrediction).delete()
    for derived in (DailySummary, AssistantMessage, TitleCategory, TitleEmbedding, Task):
        db.query(derived).delete()
    db.commit()
    return {"message": f"Successfully deleted {deleted_count} activity records, {habit_count} habits, "
                       f"{prediction_count} predictions and all summaries, messages, categories and tasks."}
