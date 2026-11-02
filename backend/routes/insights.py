"""Endpoints for semantic tasks (embeddings) and "Ask your history" (RAG)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.ask import AskAnswer, answer_question
from backend.database import get_db
from backend.llm_client import LLMClient, LLMError, get_llm_client
from backend.tasks import TaskTime, embed_new_titles, regroup_tasks, task_minutes
from backend.timeutil import local_today

router = APIRouter(prefix="/api", tags=["insights"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@router.post("/tasks/refresh")
def refresh_tasks(db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_client)):
    """Embeds new window titles, then regroups all titles into tasks."""
    try:
        embedded = embed_new_titles(db, llm)
        tasks = regroup_tasks(db, llm)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"message": f"Embedded {embedded} new title(s); {tasks} task(s) in total."}


@router.get("/tasks", response_model=list[TaskTime])
def tasks_for_day(day: date | None = None, db: Session = Depends(get_db)):
    return task_minutes(db, day or local_today())


@router.post("/ask", response_model=AskAnswer)
def ask(request: AskRequest, db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_client)):
    try:
        return answer_question(db, llm, request.question)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
