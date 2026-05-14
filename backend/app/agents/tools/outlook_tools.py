"""
Outlook tools for Calendar and Chat agents.
Wraps the existing outlook_service module functions as openai-agents function_tools.
"""
from __future__ import annotations

import json
from typing import Optional

from agents import function_tool

from app.services import outlook_service
from app.models.event import EventCreate, EventUpdate


@function_tool(strict_mode=False)
async def get_events(
    date: Optional[str] = None,
    period: str = "day",
) -> str:
    """Retrieve calendar events from Outlook for a given date and period.

    Args:
        date: Reference date in YYYY-MM-DD format. Defaults to today.
        period: Time period ('day', 'week', 'month', 'year').

    Returns:
        A JSON string with the list of event objects.
    """
    events = await outlook_service.get_events(period=period, date_ref=date)
    return json.dumps([ev.model_dump() for ev in events], default=str, ensure_ascii=False)


@function_tool(strict_mode=False)
async def create_event(
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    type: Optional[str] = None,
) -> str:
    """Create a new event in Outlook.

    Args:
        title: Event title.
        start: Start datetime in ISO format (YYYY-MM-DDTHH:MM:SS).
        end: End datetime in ISO format (YYYY-MM-DDTHH:MM:SS).
        description: Optional event description or notes.
        location: Optional event location.
        type: Optional event type ('meeting', 'call', 'focus', 'out_of_office', 'reminder', 'other').

    Returns:
        A JSON string with the created event object.
    """
    from datetime import datetime as dt
    data = EventCreate(
        title=title,
        start=dt.fromisoformat(start),
        end=dt.fromisoformat(end),
        description=description,
        location=location,
    )
    event = await outlook_service.create_event(data)
    return json.dumps(event.model_dump(), default=str, ensure_ascii=False)


@function_tool(strict_mode=False)
async def update_event(
    event_id: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """Update an existing event in Outlook.

    Args:
        event_id: The unique identifier of the Outlook event.
        title: New title for the event.
        start: New start datetime in ISO format.
        end: New end datetime in ISO format.
        description: New description.
        location: New location.

    Returns:
        A JSON string with the updated event object.
    """
    from datetime import datetime as dt
    data = EventUpdate(
        title=title,
        start=dt.fromisoformat(start) if start else None,
        end=dt.fromisoformat(end) if end else None,
        description=description,
        location=location,
    )
    event = await outlook_service.update_event(event_id, data)
    return json.dumps(event.model_dump(), default=str, ensure_ascii=False)


@function_tool(strict_mode=False)
async def delete_event(event_id: str) -> str:
    """Delete an event from Outlook.

    Args:
        event_id: The unique identifier of the Outlook event to delete.

    Returns:
        A JSON string confirming the deletion.
    """
    await outlook_service.delete_event(event_id)
    return json.dumps({"status": "deleted", "event_id": event_id})