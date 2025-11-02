"""
Unit tests for reminder service and notification scheduling.

Tests cover:
- Scheduling reminders with APScheduler
- Default reminders from CalendarListEntry
- Event-level reminder overrides
- Notification logging to NotificationLog table
- Reminder rescheduling on event updates
- Test mode with short delays
"""

import pytest
import time
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.db import Base
from app.models.models import (
    User,
    Calendar,
    Event,
    CalendarListEntry,
    Reminder,
    ReminderMethod,
    NotificationLog,
)
from app.services.reminder_service import (
    schedule_reminders,
    cancel_event_reminders,
    reschedule_reminders,
    set_event_reminders,
    get_event_reminders,
    get_notification_logs,
    stop_scheduler,
    get_scheduler,
    set_session_factory,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session with file-based SQLite for cross-session visibility."""
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Configure the reminder service to use our test session factory
    set_session_factory(TestingSessionLocal)

    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    # Clean up the temporary database file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def scheduler():
    """Get scheduler instance and ensure cleanup after test."""
    scheduler_instance = get_scheduler()
    yield scheduler_instance
    # Clean up all jobs after each test
    scheduler_instance.remove_all_jobs()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(id=uuid4(), email="testuser@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_calendar(db_session: Session, test_user):
    """Create a test calendar."""
    calendar = Calendar(
        id=uuid4(), title="Test Calendar", timezone="UTC", owner_id=test_user.id
    )
    db_session.add(calendar)
    db_session.commit()
    db_session.refresh(calendar)
    return calendar


@pytest.fixture
def calendar_list_entry_with_defaults(db_session: Session, test_user, test_calendar):
    """Create a calendar list entry with default reminders."""
    entry = CalendarListEntry(
        user_id=test_user.id,
        calendar_id=test_calendar.id,
        is_primary=True,
        default_reminders=[
            {"method": "popup", "minutes": 30},
            {"method": "email", "minutes": 60},
        ],
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


class TestScheduleReminders:
    """Test basic reminder scheduling."""

    def test_schedule_reminder_with_event_level_reminders(
        self, db_session, test_calendar, scheduler
    ):
        """Test scheduling reminders when event has explicit reminders."""
        # Create event in the future
        future_time = datetime.now() + timedelta(seconds=5)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Meeting with reminders",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-1",
        )
        db_session.add(event)
        db_session.flush()

        # Add event-level reminders
        reminder1 = Reminder(
            event_id=event.id,
            method=ReminderMethod.POPUP,
            minutes_before=2,  # 2 seconds in test mode
        )
        reminder2 = Reminder(
            event_id=event.id,
            method=ReminderMethod.EMAIL,
            minutes_before=3,  # 3 seconds in test mode
        )
        db_session.add(reminder1)
        db_session.add(reminder2)
        db_session.commit()
        db_session.refresh(event)

        # Schedule reminders in test mode (seconds instead of minutes)
        schedule_reminders(db_session, event, test_mode=True)

        # Verify jobs were scheduled
        jobs = scheduler.get_jobs()
        event_jobs = [job for job in jobs if str(event.id) in job.id]

        assert len(event_jobs) == 2
        assert any("popup" in job.id for job in event_jobs)
        assert any("email" in job.id for job in event_jobs)

    def test_schedule_reminder_with_default_reminders(
        self, db_session, test_calendar, test_user, scheduler
    ):
        """Test scheduling reminders using default reminders from CalendarListEntry."""
        # Create calendar list entry with defaults
        entry = CalendarListEntry(
            user_id=test_user.id,
            calendar_id=test_calendar.id,
            is_primary=True,
            default_reminders=[{"method": "popup", "minutes": 2}],
        )
        db_session.add(entry)
        db_session.commit()

        # Create event WITHOUT explicit reminders
        future_time = datetime.now() + timedelta(seconds=5)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Meeting with default reminders",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-2",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Schedule reminders - should use defaults
        schedule_reminders(db_session, event, test_mode=True)

        # Verify job was scheduled
        jobs = scheduler.get_jobs()
        event_jobs = [job for job in jobs if str(event.id) in job.id]

        assert len(event_jobs) == 1
        assert "popup" in event_jobs[0].id

    def test_no_reminders_scheduled_for_past_events(
        self, db_session, test_calendar, scheduler
    ):
        """Test that reminders are not scheduled for past times."""
        # Create event in the past
        past_time = datetime.now() - timedelta(hours=1)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Past meeting",
            start=past_time,
            end=past_time + timedelta(hours=1),
            iCalUID="test-event-3",
        )
        db_session.add(event)
        db_session.flush()

        # Add reminder
        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=30
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(event)

        # Try to schedule - should not create any jobs
        schedule_reminders(db_session, event, test_mode=True)

        # Verify no jobs were scheduled
        jobs = scheduler.get_jobs()
        event_jobs = [job for job in jobs if str(event.id) in job.id]

        assert len(event_jobs) == 0


class TestNotificationLogging:
    """Test that notifications are logged correctly."""

    def test_notification_is_logged_when_triggered(
        self, db_session, test_calendar, scheduler
    ):
        """Test that notification is logged to NotificationLog when reminder fires."""
        # Create event that starts in 4 seconds
        future_time = datetime.now() + timedelta(seconds=4)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Test notification logging",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-4",
        )
        db_session.add(event)
        db_session.flush()

        # Add reminder that fires in 2 seconds (2 seconds before event)
        reminder = Reminder(
            event_id=event.id,
            method=ReminderMethod.POPUP,
            minutes_before=2,  # 2 seconds in test mode
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(event)

        # Schedule reminder
        schedule_reminders(db_session, event, test_mode=True)

        # Wait for notification to fire (reminder + buffer for processing)
        time.sleep(3)

        # Close current session and create new one to see committed changes
        db_session.expire_all()

        # Check notification log
        logs = get_notification_logs(db_session, event_id=event.id)

        assert len(logs) >= 1
        log = logs[0]
        assert log.event_id == event.id
        assert log.reminder_method == ReminderMethod.POPUP
        assert log.minutes_before == 2
        assert log.event_summary == "Test notification logging"
        assert "Test notification logging" in log.message

    def test_multiple_reminders_create_multiple_logs(
        self, db_session, test_calendar, scheduler
    ):
        """Test that multiple reminders create multiple log entries."""
        # Create event that starts in 5 seconds
        future_time = datetime.now() + timedelta(seconds=5)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Multiple reminders test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-5",
        )
        db_session.add(event)
        db_session.flush()

        # Add two reminders
        reminder1 = Reminder(
            event_id=event.id,
            method=ReminderMethod.POPUP,
            minutes_before=2,  # Fires in 3 seconds
        )
        reminder2 = Reminder(
            event_id=event.id,
            method=ReminderMethod.EMAIL,
            minutes_before=3,  # Fires in 2 seconds
        )
        db_session.add(reminder1)
        db_session.add(reminder2)
        db_session.commit()
        db_session.refresh(event)

        # Schedule reminders
        schedule_reminders(db_session, event, test_mode=True)

        # Wait for both to fire (give extra buffer)
        time.sleep(4.5)

        # Expire session to see new commits
        db_session.expire_all()

        # Check notification logs
        logs = get_notification_logs(db_session, event_id=event.id)

        assert len(logs) == 2
        methods = {log.reminder_method for log in logs}
        assert ReminderMethod.POPUP in methods
        assert ReminderMethod.EMAIL in methods


class TestReminderOverrides:
    """Test event-level reminder overrides."""

    def test_event_reminders_override_defaults(
        self, db_session, test_calendar, test_user, scheduler
    ):
        """Test that event-level reminders override calendar defaults."""
        # Create calendar entry with defaults
        entry = CalendarListEntry(
            user_id=test_user.id,
            calendar_id=test_calendar.id,
            is_primary=True,
            default_reminders=[
                {"method": "popup", "minutes": 60}  # This should be ignored
            ],
        )
        db_session.add(entry)
        db_session.commit()

        # Create event with explicit reminders
        future_time = datetime.now() + timedelta(seconds=5)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Override test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-6",
        )
        db_session.add(event)
        db_session.flush()

        # Add event-level reminder (overrides default)
        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.EMAIL, minutes_before=2
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(event)

        # Get reminders - should use event-level, not defaults
        reminders = get_event_reminders(db_session, event)

        assert len(reminders) == 1
        assert reminders[0]["method"] == ReminderMethod.EMAIL
        assert reminders[0]["minutes_before"] == 2

    def test_override_reminder_5_min_triggers_once(
        self, db_session, test_calendar, test_user, scheduler
    ):
        """
        Test that override reminder = 5 min → triggers once.

        This test verifies:
        1. Event-level reminder overrides calendar defaults
        2. Reminder triggers exactly once at the specified time
        3. Notification is logged to NotificationLog
        """
        # Create calendar entry with different default
        entry = CalendarListEntry(
            user_id=test_user.id,
            calendar_id=test_calendar.id,
            is_primary=True,
            default_reminders=[
                {"method": "popup", "minutes": 30}  # This should be overridden
            ],
        )
        db_session.add(entry)
        db_session.commit()

        # Create event that starts in 8 seconds
        future_time = datetime.now() + timedelta(seconds=8)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="5 Minute Override Test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-5min-override",
        )
        db_session.add(event)
        db_session.flush()

        # Add event-level reminder: 5 minutes before (overrides default 30 min)
        # In test mode, this means 5 seconds before
        reminder = Reminder(
            event_id=event.id,
            method=ReminderMethod.POPUP,
            minutes_before=5,  # 5 seconds in test mode
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(event)

        # Verify the override is in place (not using defaults)
        reminders = get_event_reminders(db_session, event)
        assert len(reminders) == 1
        assert reminders[0]["method"] == ReminderMethod.POPUP
        assert reminders[0]["minutes_before"] == 5

        # Schedule reminder (should fire in 3 seconds: 8 - 5 = 3)
        schedule_reminders(db_session, event, test_mode=True)

        # Verify exactly 1 job was scheduled
        jobs = scheduler.get_jobs()
        event_jobs = [job for job in jobs if str(event.id) in job.id]
        assert len(event_jobs) == 1, "Should schedule exactly one reminder job"

        # Wait for the reminder to trigger (3 seconds + 1 second buffer)
        time.sleep(4)

        # Refresh session to see committed notification
        db_session.expire_all()

        # Verify exactly 1 notification was logged
        logs = get_notification_logs(db_session, event_id=event.id)
        assert len(logs) == 1, "Reminder should trigger exactly once"

        # Verify notification details
        log = logs[0]
        assert log.event_id == event.id
        assert log.user_id == test_user.id
        assert log.reminder_method == ReminderMethod.POPUP
        assert log.minutes_before == 5
        assert log.event_summary == "5 Minute Override Test"
        assert "5 Minute Override Test" in log.message
        assert "5 minute" in log.message  # Message format (test mode uses seconds but displays as minutes)

    def test_set_event_reminders_service(self, db_session, test_calendar, scheduler):
        """Test set_event_reminders service function."""
        # Create event far enough in the future
        future_time = datetime.now() + timedelta(seconds=20)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Set reminders test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-7",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Set custom reminders with buffer time
        new_reminders = [
            {"method": "popup", "minutes_before": 5},
            {"method": "email", "minutes_before": 8},
        ]

        updated_event = set_event_reminders(
            db_session, event.id, new_reminders, test_mode=True
        )

        # Verify reminders were set
        assert len(updated_event.reminders) == 2
        methods = {r.method for r in updated_event.reminders}
        assert ReminderMethod.POPUP in methods
        assert ReminderMethod.EMAIL in methods

        # Verify jobs were scheduled
        jobs = scheduler.get_jobs()
        event_jobs = [job for job in jobs if str(event.id) in job.id]
        assert len(event_jobs) == 2


class TestReminderRescheduling:
    """Test reminder rescheduling when events change."""

    def test_reschedule_reminders_after_time_change(
        self, db_session, test_calendar, scheduler
    ):
        """Test that reminders are rescheduled when event time changes."""
        # Create event
        future_time = datetime.now() + timedelta(seconds=10)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Reschedule test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-8",
        )
        db_session.add(event)
        db_session.flush()

        # Add reminder
        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=3
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(event)

        # Schedule initial reminders
        schedule_reminders(db_session, event, test_mode=True)

        # Get original job
        jobs_before = scheduler.get_jobs()
        assert len(jobs_before) >= 1

        # Change event time
        event.start = datetime.now() + timedelta(seconds=20)
        db_session.commit()

        # Reschedule reminders
        reschedule_reminders(db_session, event, test_mode=True)

        # Verify jobs were rescheduled
        jobs_after = scheduler.get_jobs()
        event_jobs = [job for job in jobs_after if str(event.id) in job.id]

        assert len(event_jobs) >= 1

    def test_cancel_event_reminders(self, db_session, test_calendar, scheduler):
        """Test cancelling all reminders for an event."""
        # Create event with multiple reminders
        future_time = datetime.now() + timedelta(seconds=10)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Cancel test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-9",
        )
        db_session.add(event)
        db_session.flush()

        # Add multiple reminders
        for i, method in enumerate([ReminderMethod.POPUP, ReminderMethod.EMAIL]):
            reminder = Reminder(event_id=event.id, method=method, minutes_before=i + 2)
            db_session.add(reminder)

        db_session.commit()
        db_session.refresh(event)

        # Schedule reminders
        schedule_reminders(db_session, event, test_mode=True)

        # Verify jobs were created
        jobs_before = scheduler.get_jobs()
        event_jobs_before = [job for job in jobs_before if str(event.id) in job.id]
        assert len(event_jobs_before) >= 2

        # Cancel all reminders for this event
        cancel_event_reminders(event.id)

        # Verify all event jobs were removed
        jobs_after = scheduler.get_jobs()
        event_jobs_after = [job for job in jobs_after if str(event.id) in job.id]
        assert len(event_jobs_after) == 0


class TestGetEventReminders:
    """Test getting reminders for events."""

    def test_get_reminders_returns_event_level_reminders(
        self, db_session, test_calendar
    ):
        """Test get_event_reminders returns event-level reminders when present."""
        # Create event with reminders
        future_time = datetime.now() + timedelta(hours=1)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Get reminders test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-10",
        )
        db_session.add(event)
        db_session.flush()

        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=30
        )
        db_session.add(reminder)
        db_session.commit()
        db_session.refresh(event)

        # Get reminders
        reminders = get_event_reminders(db_session, event)

        assert len(reminders) == 1
        assert reminders[0]["method"] == ReminderMethod.POPUP
        assert reminders[0]["minutes_before"] == 30

    def test_get_reminders_falls_back_to_defaults(
        self, db_session, test_calendar, test_user
    ):
        """Test get_event_reminders falls back to calendar defaults when no event reminders."""
        # Create calendar entry with defaults
        entry = CalendarListEntry(
            user_id=test_user.id,
            calendar_id=test_calendar.id,
            is_primary=True,
            default_reminders=[
                {"method": "popup", "minutes": 15},
                {"method": "email", "minutes": 30},
            ],
        )
        db_session.add(entry)
        db_session.commit()

        # Create event WITHOUT reminders
        future_time = datetime.now() + timedelta(hours=1)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Defaults test",
            start=future_time,
            end=future_time + timedelta(hours=1),
            iCalUID="test-event-11",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Get reminders - should return defaults
        reminders = get_event_reminders(db_session, event)

        assert len(reminders) == 2
        methods = {r["method"] for r in reminders}
        assert ReminderMethod.POPUP in methods
        assert ReminderMethod.EMAIL in methods


class TestNotificationLogQueries:
    """Test querying notification logs."""

    def test_get_notification_logs_by_event(self, db_session, test_calendar, test_user):
        """Test retrieving notification logs for a specific event."""
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Log query test",
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=1),
            iCalUID="test-event-12",
        )
        db_session.add(event)
        db_session.commit()

        # Create some logs
        for i in range(3):
            log = NotificationLog(
                event_id=event.id,
                user_id=test_user.id,
                reminder_method=ReminderMethod.POPUP,
                minutes_before=30,
                scheduled_time=datetime.now(),
                event_summary=event.summary,
                event_start=event.start,
                message=f"Test message {i}",
            )
            db_session.add(log)

        db_session.commit()

        # Query logs
        logs = get_notification_logs(db_session, event_id=event.id)

        assert len(logs) == 3
        for log in logs:
            assert log.event_id == event.id

    def test_get_notification_logs_by_user(self, db_session, test_calendar, test_user):
        """Test retrieving notification logs for a specific user."""
        # Create multiple events
        events = []
        for i in range(2):
            event = Event(
                id=uuid4(),
                calendar_id=test_calendar.id,
                summary=f"Event {i}",
                start=datetime.now(),
                end=datetime.now() + timedelta(hours=1),
                iCalUID=f"test-event-user-{i}",
            )
            db_session.add(event)
            events.append(event)

        db_session.commit()

        # Create logs for the user
        for event in events:
            log = NotificationLog(
                event_id=event.id,
                user_id=test_user.id,
                reminder_method=ReminderMethod.EMAIL,
                minutes_before=60,
                scheduled_time=datetime.now(),
                event_summary=event.summary,
                event_start=event.start,
                message="Test",
            )
            db_session.add(log)

        db_session.commit()

        # Query logs by user
        logs = get_notification_logs(db_session, user_id=test_user.id)

        assert len(logs) == 2
        for log in logs:
            assert log.user_id == test_user.id
