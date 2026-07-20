from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from .database import Base

class AppActivity(Base):
    # TODO : Might be moved to xml format for definging the models up here ..
    __tablename__ = "app_activity"

    id = Column(Integer, primary_key=True, index=True)
    
    # Timing
    start_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Application Info
    app_name = Column(String, index=True) # e.g., "Code", "Google Chrome"
    window_title = Column(String) # e.g., "AI-OS - app.py", "GitHub - ..."
    
    # Privacy First: Only integers are stored for activity!
    keystroke_count = Column(Integer, default=0)
    mouse_click_count = Column(Integer, default=0)
    
    # We could calculate duration dynamically, but storing it helps with fast analytics
    duration_seconds = Column(Integer, default=0)


class UserPreference(Base):
    __tablename__ = "user_preference"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) # e.g., "idle_timeout_seconds", "min_confidence"
    value = Column(String) # Stored as string, casted dynamically in backend
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class HabitPattern(Base):
    __tablename__ = "habit_pattern"

    id = Column(Integer, primary_key=True, index=True)
    # The sequence of apps leading to prediction, e.g. "Jira -> VS Code"
    trigger_sequence = Column(String, index=True) 
    predicted_action = Column(String) # e.g. "Terminal"
    occurrence_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.0) # Probability between 0.0 and 1.0
    last_triggered = Column(DateTime(timezone=True), server_default=func.now())


class AIPrediction(Base):
    __tablename__ = "ai_prediction"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    trigger_sequence = Column(String)
    suggested_action = Column(String)
    status = Column(String) # "accepted", "ignored", "dismissed" (this forms the AI feedback loop)
