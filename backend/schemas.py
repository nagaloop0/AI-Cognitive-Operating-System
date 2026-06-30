from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Base schema for creating a new activity record
class AppActivityCreate(BaseModel):
    app_name: str
    window_title: str

# Schema for updating an existing record (e.g., when the app is closed)
class AppActivityUpdate(BaseModel):
    end_time: datetime
    keystroke_count: int
    mouse_click_count: int
    duration_seconds: int

# Schema for reading an activity record (returned by API)
class AppActivity(BaseModel):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    app_name: str
    window_title: str
    keystroke_count: int
    mouse_click_count: int
    duration_seconds: int

    class Config:
        from_attributes = True # Allow Pydantic to work with SQLAlchemy models
