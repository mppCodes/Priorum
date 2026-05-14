"""
Notion tools for the agents.
Wraps the existing notion_service module functions as openai-agents function_tools.
"""
from __future__ import annotations

import json
from typing import Optional

from agents import function_tool

from app.services import notion_service
from app.models.task import TaskCreate, TaskUpdate, Period


@function_tool(strict_mode=False)
async def get_tasks(
    period: str = "day",
    date: Optional[str] = None,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> str:
    """Retrieve tasks from Notion filtered by the given parameters.

    Args:
        period: Time period to filter tasks ('day', 'week', 'month', 'year').
        date: Specific date in YYYY-MM-DD format.
        priority: Priority level to filter by ('alta', 'media', 'baja').
        project: Project name to filter tasks by.

    Returns:
        A JSON string with the list of task objects from Notion.
    """
    period_enum = Period(period) if period else Period.day
    tasks = await notion_service.get_tasks(
        period=period_enum,
        date_ref=date,
        priority=priority,
        project=project,
    )
    return json.dumps([task.model_dump() for task in tasks], default=str, ensure_ascii=False)


@function_tool(strict_mode=False)
async def create_task(
    title: str,
    project: str = "",
    priority: str = "media",
    deadline: str = "",
    tags: Optional[str] = None,
) -> str:
    """Create a new task in Notion.

    Args:
        title: Task title.
        project: Project name the task belongs to.
        priority: Priority level ('alta', 'media', 'baja').
        deadline: Deadline date in YYYY-MM-DD format.
        tags: Comma-separated list of tags (e.g. 'code,review,urgent').

    Returns:
        A JSON string with the created task object.
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    data = TaskCreate(
        title=title,
        project=project,
        priority=priority,  # type: ignore[arg-type]
        deadline=deadline,
        tags=tag_list,
    )
    task = await notion_service.create_task(data)
    return json.dumps(task.model_dump(), default=str, ensure_ascii=False)


@function_tool(strict_mode=False)
async def update_task(
    task_id: str,
    title: Optional[str] = None,
    priority: Optional[str] = None,
    deadline: Optional[str] = None,
    done: Optional[bool] = None,
) -> str:
    """Update a task in Notion with the provided fields.

    Args:
        task_id: The unique identifier of the Notion task to update.
        title: New title for the task.
        priority: New priority level ('alta', 'media', 'baja').
        deadline: New deadline in YYYY-MM-DD format.
        done: Whether the task is completed.

    Returns:
        A JSON string with the updated task object from Notion.
    """
    fields = {}
    if title is not None:
        fields["title"] = title
    if priority is not None:
        fields["priority"] = priority
    if deadline is not None:
        fields["deadline"] = deadline
    if done is not None:
        fields["done"] = done

    update_data = TaskUpdate(**fields)
    task = await notion_service.update_task(task_id, update_data)
    return json.dumps(task.model_dump(), default=str, ensure_ascii=False)


@function_tool(strict_mode=False)
async def delete_task(task_id: str) -> str:
    """Delete (archive) a task in Notion.

    Args:
        task_id: The unique identifier of the Notion task to delete.

    Returns:
        A JSON string confirming the deletion.
    """
    await notion_service.delete_task(task_id)
    return json.dumps({"status": "deleted", "task_id": task_id})


@function_tool(strict_mode=False)
async def add_comment(task_id: str, comment: str) -> str:
    """Add a comment to a Notion task.

    Args:
        task_id: The unique identifier of the Notion task.
        comment: The comment text to add to the task.

    Returns:
        A JSON string with the updated task object from Notion.
    """
    update_data = TaskUpdate(comments=[comment])
    task = await notion_service.update_task(task_id, update_data)
    return json.dumps(task.model_dump(), default=str, ensure_ascii=False)