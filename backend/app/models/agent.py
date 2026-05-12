from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class ChatMessage(BaseModel):
    role:      str        # "user" | "agent"
    content:   str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    message:   str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PriorityItem(BaseModel):
    rank:  int
    title: str
    why:   str
    time:  Optional[str] = None   # ej: "45 min"
    tag:   Optional[str] = None   # "alta" | "media" | "baja"


class PrioritiesRequest(BaseModel):
    tasks:  list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    date:   Optional[str] = None


class PrioritiesResponse(BaseModel):
    priorities: list[PriorityItem]
    reasoning:  str = ""


class ScheduleRequest(BaseModel):
    tasks:      list[dict[str, Any]] = Field(default_factory=list)
    events:     list[dict[str, Any]] = Field(default_factory=list)
    date:       Optional[str] = None
    free_slots: list[dict[str, str]] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    schedule:  list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""


class HistoryResponse(BaseModel):
    messages: list[ChatMessage]