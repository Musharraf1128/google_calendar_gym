"""
Task management endpoints.

Provides endpoints for:
- Creating tasks (standalone or linked to events)
- Listing tasks for a user
- Updating task status (toggle completion)
- Managing task details
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID

from app.db import get_db
from app.models.models import Task, User, Event, TaskStatus
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
)

router = APIRouter()


@router.get("/users/{user_id}/tasks", response_model=List[TaskResponse])
async def get_user_tasks(
    user_id: UUID,
    status_filter: Optional[str] = Query(
        None, description="Filter by status: needsAction or completed"
    ),
    include_completed: bool = Query(True, description="Include completed tasks"),
    related_event_id: Optional[UUID] = Query(
        None, description="Filter by related event"
    ),
    db: Session = Depends(get_db),
):
    """
    Get all tasks for a user.

    Supports filtering by:
    - status: needsAction or completed
    - include_completed: Whether to show completed tasks
    - related_event_id: Show only tasks linked to a specific event

    Args:
        user_id: UUID of the user
        status_filter: Optional status filter
        include_completed: Include completed tasks (default: True)
        related_event_id: Optional event ID filter
        db: Database session

    Returns:
        List of tasks
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    # Build query
    query = db.query(Task).filter(Task.user_id == user_id)

    # Apply status filter
    if status_filter:
        if status_filter == "needsAction":
            query = query.filter(Task.status == TaskStatus.NEEDS_ACTION)
        elif status_filter == "completed":
            query = query.filter(Task.status == TaskStatus.COMPLETED)

    # Filter completed tasks if requested
    if not include_completed:
        query = query.filter(Task.status == TaskStatus.NEEDS_ACTION)

    # Filter by related event if provided
    if related_event_id:
        query = query.filter(Task.related_event_id == related_event_id)

    # Order by: incomplete tasks first, then by due date (nearest first), then by created date
    query = query.order_by(
        Task.status.desc(),  # NEEDS_ACTION before COMPLETED
        Task.due.asc().nullslast(),  # Tasks with due dates first, sorted by date
        Task.created_at.desc(),  # Newest first for tasks without due dates
    )

    tasks = query.all()
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific task by ID.

    Args:
        task_id: UUID of the task
        db: Database session

    Returns:
        Task details
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    return task


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task.

    Tasks can be:
    - Standalone (no related_event_id)
    - Linked to an event (related_event_id set)

    Args:
        task_data: Task creation data
        db: Database session

    Returns:
        Created task
    """
    # Verify user exists
    user = db.query(User).filter(User.id == task_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {task_data.user_id} not found",
        )

    # Verify event exists if related_event_id is provided
    if task_data.related_event_id:
        event = db.query(Event).filter(Event.id == task_data.related_event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {task_data.related_event_id} not found",
            )

    # Create task
    new_task = Task(
        user_id=task_data.user_id,
        title=task_data.title,
        notes=task_data.notes,
        due=task_data.due,
        status=task_data.status,
        related_event_id=task_data.related_event_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID, task_update: TaskUpdate, db: Session = Depends(get_db)
):
    """
    Update a task.

    Supports updating:
    - title, notes, due date
    - status (toggle between needsAction and completed)
    - related_event_id (link/unlink event)

    When status is changed to 'completed', completed_at is automatically set.
    When status is changed back to 'needsAction', completed_at is cleared.

    Args:
        task_id: UUID of the task to update
        task_update: Fields to update
        db: Database session

    Returns:
        Updated task
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    # Update fields if provided
    update_data = task_update.model_dump(exclude_unset=True)

    # Handle status change
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
            # Mark as completed
            task.completed_at = datetime.now(timezone.utc)
        elif (
            new_status == TaskStatus.NEEDS_ACTION
            and task.status == TaskStatus.COMPLETED
        ):
            # Reopen task
            task.completed_at = None

    # Apply updates
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a task.

    Args:
        task_id: UUID of the task to delete
        db: Database session
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    db.delete(task)
    db.commit()

    return None


@router.post("/tasks/{task_id}/toggle", response_model=TaskResponse)
async def toggle_task_completion(task_id: UUID, db: Session = Depends(get_db)):
    """
    Toggle task completion status.

    Convenience endpoint for:
    - needsAction → completed (sets completed_at)
    - completed → needsAction (clears completed_at)

    Args:
        task_id: UUID of the task
        db: Database session

    Returns:
        Updated task
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    # Toggle status
    if task.status == TaskStatus.NEEDS_ACTION:
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.status = TaskStatus.NEEDS_ACTION
        task.completed_at = None

    db.commit()
    db.refresh(task)

    return task


@router.get("/events/{event_id}/tasks", response_model=List[TaskResponse])
async def get_event_tasks(event_id: UUID, db: Session = Depends(get_db)):
    """
    Get all tasks linked to a specific event.

    Args:
        event_id: UUID of the event
        db: Database session

    Returns:
        List of tasks linked to the event
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    # Get linked tasks
    tasks = (
        db.query(Task)
        .filter(Task.related_event_id == event_id)
        .order_by(Task.status.desc(), Task.created_at.desc())
        .all()
    )

    return tasks
