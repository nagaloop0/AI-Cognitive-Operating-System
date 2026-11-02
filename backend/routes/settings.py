"""Endpoints to read and change the assistant settings."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.settings import AssistantSettings, load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AssistantSettings)
def get_settings(db: Session = Depends(get_db)):
    return load_settings(db)


@router.put("", response_model=AssistantSettings)
def update_settings(updates: dict[str, Any], db: Session = Depends(get_db)):
    """Send only the settings to change, e.g. {"tone": "strict", "away_minutes": 20}."""
    try:
        return save_settings(db, updates)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors(include_url=False, include_context=False))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
