"""
Tests for Task functionality.

This module tests:
- Creating standalone tasks
- Creating tasks linked to events
- Toggling task completion
- Listing tasks for a user
- Task filtering (status, related event)
- Event + linked task → toggle completion updates UI
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models.models import (
    User,
    Calendar,
    Event,
    Task,
    TaskStatus,
    EventStatus,
)


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_tasks.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create and drop tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a database session for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="testuser@example.com",
        name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_calendar(db, test_user):
    """Create a test calendar."""
    calendar = Calendar(
        id=uuid4(),
        title="Test Calendar",
        timezone="UTC",
        owner_id=test_user.id,
    )
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


@pytest.fixture
def test_event(db, test_calendar, test_user):
    """Create a test event."""
    event = Event(
        id=uuid4(),
        calendar_id=test_calendar.id,
        summary="Team Meeting",
        description="Discuss project updates",
        start=datetime(2025, 11, 20, 14, 0, 0, tzinfo=timezone.utc),
        end=datetime(2025, 11, 20, 15, 0, 0, tzinfo=timezone.utc),
        status=EventStatus.CONFIRMED,
        organizer_id=test_user.id,
        creator_id=test_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


class TestTaskCreation:
    """Test task creation."""

    def test_create_standalone_task(self, db, test_user):
        """Test creating a standalone task (not linked to any event)."""
        response = client.post(
            "/api/tasks",
            json={
                "user_id": str(test_user.id),
                "title": "Buy groceries",
                "notes": "Milk, bread, eggs",
                "due": "2025-11-25T18:00:00Z",
                "status": "needsAction",
                "related_event_id": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy groceries"
        assert data["notes"] == "Milk, bread, eggs"
        assert data["status"] == "needsAction"
        assert data["related_event_id"] is None
        assert data["completed_at"] is None

    def test_create_task_linked_to_event(self, db, test_user, test_event):
        """Test creating a task linked to an event."""
        response = client.post(
            "/api/tasks",
            json={
                "user_id": str(test_user.id),
                "title": "Prepare presentation slides",
                "notes": "For the team meeting",
                "due": test_event.start.isoformat(),
                "status": "needsAction",
                "related_event_id": str(test_event.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Prepare presentation slides"
        assert data["related_event_id"] == str(test_event.id)
        assert data["status"] == "needsAction"

    def test_create_task_without_due_date(self, db, test_user):
        """Test creating a task without a due date."""
        response = client.post(
            "/api/tasks",
            json={
                "user_id": str(test_user.id),
                "title": "Read documentation",
                "status": "needsAction",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Read documentation"
        assert data["due"] is None


class TestTaskRetrieval:
    """Test task retrieval."""

    def test_get_user_tasks(self, db, test_user):
        """Test getting all tasks for a user."""
        # Create multiple tasks
        task1 = Task(
            user_id=test_user.id,
            title="Task 1",
            status=TaskStatus.NEEDS_ACTION,
        )
        task2 = Task(
            user_id=test_user.id,
            title="Task 2",
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        task3 = Task(
            user_id=test_user.id,
            title="Task 3",
            status=TaskStatus.NEEDS_ACTION,
            due=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add_all([task1, task2, task3])
        db.commit()

        response = client.get(f"/api/users/{test_user.id}/tasks")

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 3

    def test_filter_tasks_by_status(self, db, test_user):
        """Test filtering tasks by status."""
        # Create tasks with different statuses
        task1 = Task(
            user_id=test_user.id,
            title="Active Task",
            status=TaskStatus.NEEDS_ACTION,
        )
        task2 = Task(
            user_id=test_user.id,
            title="Completed Task",
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        db.add_all([task1, task2])
        db.commit()

        # Get only active tasks
        response = client.get(
            f"/api/users/{test_user.id}/tasks",
            params={"status_filter": "needsAction"},
        )

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["status"] == "needsAction"

    def test_get_event_linked_tasks(self, db, test_user, test_event):
        """Test getting all tasks linked to an event."""
        # Create tasks linked to event
        task1 = Task(
            user_id=test_user.id,
            title="Prepare agenda",
            related_event_id=test_event.id,
            status=TaskStatus.NEEDS_ACTION,
        )
        task2 = Task(
            user_id=test_user.id,
            title="Send invites",
            related_event_id=test_event.id,
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        # Unrelated task
        task3 = Task(
            user_id=test_user.id,
            title="Unrelated task",
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add_all([task1, task2, task3])
        db.commit()

        response = client.get(f"/api/events/{test_event.id}/tasks")

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 2
        assert all(task["related_event_id"] == str(test_event.id) for task in tasks)


class TestTaskCompletion:
    """Test task completion toggling."""

    def test_toggle_task_to_completed(self, db, test_user):
        """Test toggling a task from needsAction to completed."""
        # Create task
        task = Task(
            user_id=test_user.id,
            title="Complete this task",
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Toggle to completed
        response = client.post(f"/api/tasks/{task.id}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

        # Verify in database
        db.refresh(task)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_toggle_task_to_needs_action(self, db, test_user):
        """Test toggling a completed task back to needsAction."""
        # Create completed task
        task = Task(
            user_id=test_user.id,
            title="Completed task",
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Toggle back to needsAction
        response = client.post(f"/api/tasks/{task.id}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "needsAction"
        assert data["completed_at"] is None

        # Verify in database
        db.refresh(task)
        assert task.status == TaskStatus.NEEDS_ACTION
        assert task.completed_at is None

    def test_event_linked_task_toggle_completion(self, db, test_user, test_event):
        """
        KEY TEST: Test that toggling a task linked to an event updates correctly.

        This test verifies:
        1. Task can be linked to an event
        2. Task can be toggled to completed
        3. Task status persists in database
        4. Completed timestamp is set
        5. Task can be toggled back to needsAction
        """
        # Create task linked to event
        response = client.post(
            "/api/tasks",
            json={
                "user_id": str(test_user.id),
                "title": "Prepare presentation for meeting",
                "notes": "Create slides and practice",
                "due": test_event.start.isoformat(),
                "status": "needsAction",
                "related_event_id": str(test_event.id),
            },
        )

        assert response.status_code == 201
        task_data = response.json()
        task_id = task_data["id"]

        # Verify task is linked to event
        assert task_data["related_event_id"] == str(test_event.id)
        assert task_data["status"] == "needsAction"
        assert task_data["completed_at"] is None

        # Toggle task to completed
        toggle_response = client.post(f"/api/tasks/{task_id}/toggle")

        assert toggle_response.status_code == 200
        completed_task = toggle_response.json()
        assert completed_task["status"] == "completed"
        assert completed_task["completed_at"] is not None
        assert completed_task["related_event_id"] == str(test_event.id)

        # Verify task appears in event's task list
        event_tasks_response = client.get(f"/api/events/{test_event.id}/tasks")
        assert event_tasks_response.status_code == 200
        event_tasks = event_tasks_response.json()
        assert len(event_tasks) == 1
        assert event_tasks[0]["id"] == task_id
        assert event_tasks[0]["status"] == "completed"

        # Toggle back to needsAction
        toggle_back_response = client.post(f"/api/tasks/{task_id}/toggle")

        assert toggle_back_response.status_code == 200
        reopened_task = toggle_back_response.json()
        assert reopened_task["status"] == "needsAction"
        assert reopened_task["completed_at"] is None


class TestTaskUpdate:
    """Test task updates."""

    def test_update_task_title(self, db, test_user):
        """Test updating a task's title."""
        task = Task(
            user_id=test_user.id,
            title="Original title",
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        response = client.patch(
            f"/api/tasks/{task.id}",
            json={"title": "Updated title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated title"

    def test_update_task_due_date(self, db, test_user):
        """Test updating a task's due date."""
        task = Task(
            user_id=test_user.id,
            title="Task with due date",
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        new_due = datetime(2025, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        response = client.patch(
            f"/api/tasks/{task.id}",
            json={"due": new_due.isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["due"] is not None

    def test_update_task_status_sets_completed_at(self, db, test_user):
        """Test that updating status to completed sets completed_at."""
        task = Task(
            user_id=test_user.id,
            title="Task to complete",
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        response = client.patch(
            f"/api/tasks/{task.id}",
            json={"status": "completed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None


class TestTaskDeletion:
    """Test task deletion."""

    def test_delete_task(self, db, test_user):
        """Test deleting a task."""
        task = Task(
            user_id=test_user.id,
            title="Task to delete",
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        response = client.delete(f"/api/tasks/{task_id}")

        assert response.status_code == 204

        # Verify task is deleted
        deleted_task = db.query(Task).filter(Task.id == task_id).first()
        assert deleted_task is None

    def test_delete_task_linked_to_event_does_not_delete_event(
        self, db, test_user, test_event
    ):
        """Test that deleting a task linked to an event doesn't delete the event."""
        task = Task(
            user_id=test_user.id,
            title="Linked task",
            related_event_id=test_event.id,
            status=TaskStatus.NEEDS_ACTION,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        response = client.delete(f"/api/tasks/{task.id}")

        assert response.status_code == 204

        # Verify event still exists
        event = db.query(Event).filter(Event.id == test_event.id).first()
        assert event is not None
