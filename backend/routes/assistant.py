"""Endpoints for the assistant's messages (welcome back, end of day, nudges)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.assistant import MessageKind
from backend.database import get_db
from backend.models import AssistantMessage

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    kind: MessageKind
    title: str
    body: str
    is_read: bool


@router.get("/messages", response_model=list[AssistantMessageItem])
def list_messages(unread_only: bool = False, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(AssistantMessage)
    if unread_only:
        query = query.filter(AssistantMessage.is_read.is_(False))
    return query.order_by(AssistantMessage.id.desc()).limit(limit).all()


@router.post("/messages/{message_id}/read", response_model=AssistantMessageItem)
def mark_read(message_id: int, db: Session = Depends(get_db)):
    message = db.get(AssistantMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_read = True
    db.commit()
    return message
