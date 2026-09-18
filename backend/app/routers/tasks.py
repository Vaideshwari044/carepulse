"""FastAPI Router for Clinician Tasks and System Notifications (/api/v1/tasks & /api/v1/notifications)."""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Notification, Task, User
from app.schemas import NotificationOut, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List clinician workflow tasks."""
    query = select(Task).order_by(desc(Task.created_at))
    if status_filter:
        query = query.where(Task.status == status_filter)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return [TaskOut.model_validate(t) for t in tasks]


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new task."""
    task = Task(
        title=body.title,
        description=body.description,
        priority=body.priority,
        patient_id=body.patient_id,
        assignee_id=current_user.id,
        due_date=body.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return TaskOut.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update task status, priority, or details."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found", "details": {}}},
        )

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.priority is not None:
        task.priority = body.priority
    if body.status is not None:
        task.status = body.status
    if body.due_date is not None:
        task.due_date = body.due_date

    await db.commit()
    await db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notifications for current user or system."""
    query = select(Notification).order_by(desc(Notification.created_at)).limit(50)
    if category:
        query = query.where(Notification.category == category)
    result = await db.execute(query)
    notifications = result.scalars().all()
    return [NotificationOut.model_validate(n) for n in notifications]


@router.post("/notifications/mark-read", status_code=status.HTTP_200_OK)
async def mark_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all unread notifications as read."""
    result = await db.execute(select(Notification).where(Notification.is_read == False))
    unread = result.scalars().all()
    for n in unread:
        n.is_read = True
    await db.commit()
    return {"message": "Notifications marked as read", "count": len(unread)}
