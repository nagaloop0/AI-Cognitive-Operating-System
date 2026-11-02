import os

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base

load_dotenv()

# Length of one title vector; must match EMBED_MODEL (nomic-embed-text = 768).
# Changing the model to one with another size needs a new title_embedding table.
EMBEDDING_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "768"))

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


class DailySummary(Base):
    """One generated summary per local day, cached because the model takes seconds."""
    __tablename__ = "daily_summary"

    id = Column(Integer, primary_key=True)
    day = Column(Date, unique=True, index=True, nullable=False)
    payload = Column(JSON, nullable=False)          # the DailySummaryResult as JSON
    source = Column(String, nullable=False)         # "llm" or "fallback"
    model = Column(String, nullable=True)
    is_partial = Column(Boolean, default=False)     # True when made before the day was over
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AssistantMessage(Base):
    """Messages the assistant leaves for the user (welcome back, end of day, nudges)."""
    __tablename__ = "assistant_message"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    kind = Column(String, nullable=False)           # "welcome_back", "end_of_day", "nudge", "unread"
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)


class TitleCategory(Base):
    """Category of one window title: work, learning, fun, communication or other."""
    __tablename__ = "title_category"
    __table_args__ = (UniqueConstraint("app_name", "window_title"),)

    id = Column(Integer, primary_key=True)
    app_name = Column(String, nullable=False)
    window_title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    source = Column(String, nullable=False)         # "rule", "llm" or "user" (a user correction always wins)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Task(Base):
    """A group of similar window titles that belong to one piece of work."""
    __tablename__ = "task"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TitleEmbedding(Base):
    """Vector of one window title. pgvector in PostgreSQL; plain JSON in the SQLite test database."""
    __tablename__ = "title_embedding"
    __table_args__ = (UniqueConstraint("app_name", "window_title"),)

    id = Column(Integer, primary_key=True)
    app_name = Column(String, nullable=False)
    window_title = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS).with_variant(JSON(), "sqlite"), nullable=False)
    task_id = Column(Integer, ForeignKey("task.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
