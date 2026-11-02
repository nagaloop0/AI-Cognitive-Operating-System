"""Endpoints for the day digest, the AI daily summary and the local model status."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.digest import DayDigest, build_day_digest
from backend.llm_client import LLMClient, get_llm_client
from backend.settings import load_settings
from backend.summary import DailySummaryResult, get_daily_summary
from backend.timeutil import local_today

router = APIRouter(prefix="/api", tags=["summary"])


class LLMStatus(BaseModel):
    available: bool
    model: str
    url: str


@router.get("/summary/daily", response_model=DailySummaryResult)
def daily_summary(day: date | None = None, refresh: bool = False, db: Session = Depends(get_db),
                  llm: LLMClient = Depends(get_llm_client)):
    """AI summary of one local day (default: today). Cached; `refresh=true` makes a new one."""
    try:
        return get_daily_summary(db, day or local_today(), llm, refresh=refresh)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary/digest", response_model=DayDigest)
def day_digest(day: date | None = None, db: Session = Depends(get_db)):
    """The plain numbers behind the summary (no AI)."""
    return build_day_digest(db, day or local_today(), load_settings(db).private_apps)


@router.get("/llm/status", response_model=LLMStatus)
def llm_status(llm: LLMClient = Depends(get_llm_client)):
    return LLMStatus(available=llm.is_available(), model=llm.model, url=llm.base_url)
