from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    alta  = "alta"
    media = "media"
    baja  = "baja"


class Period(str, Enum):
    day   = "day"
    week  = "week"
    month = "month"
    year  = "year"


class TaskBase(BaseModel):
    title:    str
    project:  str = ""
    priority: Priority = Priority.media
    deadline: str = ""
    tags:     list[str] = Field(default_factory=list)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title:    Optional[str]      = None
    project:  Optional[str]      = None
    priority: Optional[Priority] = None
    deadline: Optional[str]      = None
    tags:     Optional[list[str]] = None
    done:     Optional[bool]     = None
    subtasks: Optional[list[str]] = None
    comments: Optional[list[str]] = None


class Task(TaskBase):
    id:        str
    done:      bool = False
    subtasks:  list[str] = Field(default_factory=list)
    comments:  list[str] = Field(default_factory=list)
    notion_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}