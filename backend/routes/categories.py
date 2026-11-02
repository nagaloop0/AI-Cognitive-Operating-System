"""Endpoints for title categories (work, learning, fun, communication, other)."""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.categories import categorize_day, set_category
from backend.database import get_db
from backend.digest import load_segments
from backend.llm_client import LLMClient, LLMError, get_llm_client
from backend.models import TitleCategory
from backend.timeutil import local_day_bounds, local_today

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategorizedTitle(BaseModel):
    app_name: str
    window_title: str
    category: str | None
    source: str | None
    minutes: int


class DayCategories(BaseModel):
    day: date
    category_minutes: dict[str, int]
    titles: list[CategorizedTitle]


class CategoryUpdate(BaseModel):
    app_name: str
    window_title: str
    category: str


@router.get("", response_model=DayCategories)
def day_categories(day: date | None = None, db: Session = Depends(get_db)):
    """Every title used on the day with its category and minutes, most used first."""
    day = day or local_today()
    start, end = local_day_bounds(day)
    seconds: dict[tuple[str, str], float] = defaultdict(float)
    for seg in load_segments(db, start, end):
        seconds[(seg.app_name, seg.title)] += seg.seconds
    labels = {(r.app_name, r.window_title): r for r in db.query(TitleCategory).all()}

    titles, per_category = [], defaultdict(float)
    for (app_name, title), secs in sorted(seconds.items(), key=lambda item: item[1], reverse=True):
        label = labels.get((app_name, title))
        if label:
            per_category[label.category] += secs
        titles.append(CategorizedTitle(app_name=app_name, window_title=title, minutes=round(secs / 60),
                                       category=label.category if label else None,
                                       source=label.source if label else None))
    minutes = {name: round(s / 60) for name, s in sorted(per_category.items(), key=lambda i: i[1], reverse=True)}
    return DayCategories(day=day, category_minutes=minutes, titles=titles)


@router.post("/refresh")
def refresh_categories(day: date | None = None, db: Session = Depends(get_db),
                       llm: LLMClient = Depends(get_llm_client)):
    """Labels any new titles of the day now (rules first, then the local model)."""
    try:
        added = categorize_day(db, day or local_today(), llm)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"message": f"Labelled {added} new title(s)."}


@router.put("", response_model=CategorizedTitle)
def correct_category(update: CategoryUpdate, db: Session = Depends(get_db)):
    """Your correction always wins over rules and the model."""
    try:
        row = set_category(db, update.app_name, update.window_title, update.category)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return CategorizedTitle(app_name=row.app_name, window_title=row.window_title, category=row.category,
                            source=row.source, minutes=0)
