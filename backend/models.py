from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class AppActivity(Base):
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
