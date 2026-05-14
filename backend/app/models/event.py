from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    meeting = "meeting"
    reunion = "reunion"
    call = "call"
    focus = "focus"
    personal = "personal"
    bloqueo = "bloqueo"
    out_of_office = "out_of_office"
    reminder = "reminder"
    other = "other"


class Attendee(BaseModel):
    email: str
    name: Optional[str] = None


class EventBase(BaseModel):
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[Attendee]] = []
    type: Optional[EventType] = None  # tipo del evento (si aplica)


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[Attendee]] = None
    type: Optional[EventType] = None


class Event(BaseModel):
    id: Optional[str] = Field(default=None, description="Mongo ObjectId (string)")
    external_id: Optional[str] = None  # ID del evento en Microsoft Graph
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Optional[str] = None
    attendees: Optional[List[Attendee]] = []
    source: Optional[str] = "outlook"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
