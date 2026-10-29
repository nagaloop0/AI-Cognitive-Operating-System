from pydantic import BaseModel
from datetime import datetime

# Base schema for creating a new activity record
class AppActivityCreate(BaseModel):
    app_name: str
    window_title: str

# Schema for updating an existing record (e.g., when the session ends)
class AppActivityUpdate(BaseModel):
    end_time: datetime
    keystroke_count: int
    mouse_click_count: int
    duration_seconds: int

# Schema for reading a raw activity record
class AppActivitySchema(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime | None = None
    app_name: str
    window_title: str
    keystroke_count: int
    mouse_click_count: int
    duration_seconds: int

    class Config:
        from_attributes = True

# --- API DTOs (Data Transfer Objects for Dashboard Responses) ---

class OverallSummary(BaseModel):
    total_duration_seconds: int
    total_keystrokes: int
    total_clicks: int
    total_sessions: int

class AppSummary(BaseModel):
    app_name: str
    total_duration_seconds: int
    total_keystrokes: int
    total_clicks: int
    session_count: int

class TimelineItem(BaseModel):
    id: int
    app_name: str
    window_title: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: int
    keystroke_count: int
    mouse_click_count: int

    class Config:
        from_attributes = True

class PreferenceStatus(BaseModel):
    is_tracking_paused: bool

class NotificationStatus(BaseModel):
    desktop_notifications_enabled: bool

class MessageResponse(BaseModel):
    message: str

class HabitPatternItem(BaseModel):
    id: int
    trigger_sequence: str
    predicted_action: str
    occurrence_count: int
    confidence: float
    last_triggered: datetime | None = None

    class Config:
        from_attributes = True

class PredictionItem(BaseModel):
    id: int
    timestamp: datetime
    trigger_sequence: str
    suggested_action: str
    status: str

    class Config:
        from_attributes = True

class DashboardData(BaseModel):
    summary: OverallSummary
    apps: list[AppSummary]
    timeline: list[TimelineItem]
    preference: PreferenceStatus
    patterns: list[HabitPatternItem] = []
    recent_predictions: list[PredictionItem] = []

