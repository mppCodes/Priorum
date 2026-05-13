from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TaskCache(BaseModel):
    id: Optional[str] = Field(default=None, description="Mongo ObjectId (string)")
    external_id: str  # ID de la tarea en Notion
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = []
    source: Optional[str] = "notion"
    raw: Optional[Dict[str, Any]] = None  # documento completo original si quieres guardarlo
    cached_at: datetime = Field(default_factory=datetime.utcnow)  # usado para TTL

class EventCache(BaseModel):
    id: Optional[str] = Field(default=None)
    external_id: str  # ID del evento en Microsoft Graph
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Optional[str] = None
    attendees: Optional[List[Dict[str, Any]]] = []
    source: Optional[str] = "outlook"
    raw: Optional[Dict[str, Any]] = None
    cached_at: datetime = Field(default_factory=datetime.utcnow)  # usado para TTL
