from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    reunion  = "reunion"
    personal = "personal"
    bloqueo  = "bloqueo"


class EventBase(BaseModel):
    title:     str
    date:      str                        # YYYY-MM-DD
    time:      str                        # HH:MM
    duration:  int = 30                   # minutos
    type:      EventType = EventType.personal
    notes:     str = ""
    attendees: list[str] = Field(default_factory=list)


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title:     Optional[str]       = None
    date:      Optional[str]       = None
    time:      Optional[str]       = None
    duration:  Optional[int]       = None
    type:      Optional[EventType] = None
    notes:     Optional[str]       = None
    attendees: Optional[list[str]] = None


class Event(EventBase):
    id:           str
    outlook_id:   Optional[str] = None
    teams_url:    Optional[str] = None
    created_at:   Optional[datetime] = None
    updated_at:   Optional[datetime] = None

    model_config = {"from_attributes": True}