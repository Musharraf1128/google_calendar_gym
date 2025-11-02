"""
Tests for SQLAlchemy models.

Tests model creation, relationships, constraints, and validations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    User,
    Calendar,
    Event,
    EventAttendee,
    CalendarACL,
    CalendarListEntry,
    Reminder,
    CalendarRole,
    EventStatus,
    AttendeeResponseStatus,
    ReminderMethod,
    utc_now,
)
from app.db import SessionLocal, engine, Base


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestUtcNow:
    """Test the utc_now helper function."""

    def test_utc_now_returns_timezone_aware_datetime(self):
        """Test that utc_now returns a timezone-aware datetime."""
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_utc_now_is_recent(self):
        """Test that utc_now returns a recent datetime."""
        now = utc_now()
        delta = datetime.now(timezone.utc) - now
        assert delta.total_seconds() < 1


class TestUserModel:
    """Test the User model."""

    def test_create_user(self, db_session):
        """Test creating a basic user."""
        user = User(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_email_unique(self, db_session):
        """Test that user email must be unique."""
        user1 = User(email="test@example.com", name="User 1")
        db_session.add(user1)
        db_session.commit()

        user2 = User(email="test@example.com", name="User 2")
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_email_required(self, db_session):
        """Test that user email is required."""
        user = User(name="Test User")
        db_session.add(user)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_auto_generated_id(self, db_session):
        """Test that user ID is auto-generated."""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert isinstance(user.id, uuid4().__class__)


class TestCalendarModel:
    """Test the Calendar model."""

    def test_create_calendar(self, db_session):
        """Test creating a basic calendar."""
        user = User(email="owner@example.com", name="Owner")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(
            title="My Calendar",
            timezone="America/New_York",
            owner_id=user.id,
            description="Test calendar",
        )
        db_session.add(calendar)
        db_session.commit()

        assert calendar.id is not None
        assert calendar.title == "My Calendar"
        assert calendar.timezone == "America/New_York"
        assert calendar.owner_id == user.id
        assert calendar.description == "Test calendar"

    def test_calendar_owner_relationship(self, db_session):
        """Test calendar owner relationship."""
        user = User(email="owner@example.com", name="Owner")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="My Calendar", owner_id=user.id)
        db_session.add(calendar)
        db_session.commit()
        db_session.refresh(calendar)

        assert calendar.owner is not None
        assert calendar.owner.id == user.id
        assert calendar.owner.email == "owner@example.com"

    def test_calendar_default_timezone(self, db_session):
        """Test calendar default timezone is UTC."""
        user = User(email="owner@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.commit()

        assert calendar.timezone == "UTC"

    def test_calendar_requires_owner(self, db_session):
        """Test that calendar requires an owner."""
        calendar = Calendar(title="Test")
        db_session.add(calendar)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestEventModel:
    """Test the Event model."""

    def test_create_event(self, db_session):
        """Test creating a basic event."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event = Event(
            calendar_id=calendar.id,
            summary="Test Event",
            description="Test description",
            start=now,
            end=now + timedelta(hours=1),
            location="Test Location",
            status=EventStatus.CONFIRMED,
            is_all_day=False,
        )
        db_session.add(event)
        db_session.commit()

        assert event.id is not None
        assert event.summary == "Test Event"
        assert event.description == "Test description"
        assert event.location == "Test Location"
        assert event.status == EventStatus.CONFIRMED
        assert event.is_all_day is False

    def test_event_calendar_relationship(self, db_session):
        """Test event calendar relationship."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event = Event(
            calendar_id=calendar.id,
            summary="Test",
            start=now,
            end=now + timedelta(hours=1),
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.calendar is not None
        assert event.calendar.id == calendar.id

    def test_event_icaluid_composite_unique(self, db_session):
        """Test that iCalUID is unique per calendar."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        ical_uid = "test-event@calendar.app"

        event1 = Event(
            calendar_id=calendar.id,
            iCalUID=ical_uid,
            summary="Event 1",
            start=now,
            end=now + timedelta(hours=1),
        )
        db_session.add(event1)
        db_session.commit()

        # Same iCalUID in same calendar should fail
        event2 = Event(
            calendar_id=calendar.id,
            iCalUID=ical_uid,
            summary="Event 2",
            start=now,
            end=now + timedelta(hours=1),
        )
        db_session.add(event2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_event_icaluid_allows_same_across_calendars(self, db_session):
        """Test that same iCalUID is allowed across different calendars."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar1 = Calendar(title="Cal 1", owner_id=user.id)
        calendar2 = Calendar(title="Cal 2", owner_id=user.id)
        db_session.add_all([calendar1, calendar2])
        db_session.flush()

        now = datetime.now(timezone.utc)
        ical_uid = "shared-event@calendar.app"

        event1 = Event(
            calendar_id=calendar1.id,
            iCalUID=ical_uid,
            summary="Event 1",
            start=now,
            end=now + timedelta(hours=1),
        )
        event2 = Event(
            calendar_id=calendar2.id,
            iCalUID=ical_uid,
            summary="Event 2",
            start=now,
            end=now + timedelta(hours=1),
        )
        db_session.add_all([event1, event2])
        db_session.commit()  # Should succeed

        assert event1.id != event2.id
        assert event1.iCalUID == event2.iCalUID

    def test_event_recurrence_stored_as_list(self, db_session):
        """Test that recurrence is stored as list."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event = Event(
            calendar_id=calendar.id,
            summary="Recurring Event",
            start=now,
            end=now + timedelta(hours=1),
            recurrence=["RRULE:FREQ=DAILY;COUNT=5"],
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.recurrence is not None
        assert isinstance(event.recurrence, list)
        assert event.recurrence[0] == "RRULE:FREQ=DAILY;COUNT=5"


class TestEventAttendeeModel:
    """Test the EventAttendee model."""

    def test_create_attendee(self, db_session):
        """Test creating an event attendee."""
        user = User(email="user@example.com")
        attendee_user = User(email="attendee@example.com", name="Attendee")
        db_session.add_all([user, attendee_user])
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event = Event(
            calendar_id=calendar.id,
            summary="Meeting",
            start=now,
            end=now + timedelta(hours=1),
        )
        db_session.add(event)
        db_session.flush()

        attendee = EventAttendee(
            event_id=event.id,
            user_id=attendee_user.id,
            email="attendee@example.com",
            display_name="Attendee",
            response_status=AttendeeResponseStatus.NEEDS_ACTION,
            is_organizer=False,
            is_optional=False,
        )
        db_session.add(attendee)
        db_session.commit()

        assert attendee.id is not None
        assert attendee.email == "attendee@example.com"
        assert attendee.response_status == AttendeeResponseStatus.NEEDS_ACTION


class TestCalendarACLModel:
    """Test the CalendarACL model."""

    def test_create_acl(self, db_session):
        """Test creating a calendar ACL entry."""
        user = User(email="owner@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Shared Calendar", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        acl = CalendarACL(
            calendar_id=calendar.id,
            grantee="reader@example.com",
            role=CalendarRole.READER,
        )
        db_session.add(acl)
        db_session.commit()

        assert acl.id is not None
        assert acl.grantee == "reader@example.com"
        assert acl.role == CalendarRole.READER


class TestCalendarListEntryModel:
    """Test the CalendarListEntry model."""

    def test_create_calendar_list_entry(self, db_session):
        """Test creating a calendar list entry."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        entry = CalendarListEntry(
            user_id=user.id,
            calendar_id=calendar.id,
            color="#4285f4",
            is_primary=True,
            default_reminders=[
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60},
            ],
        )
        db_session.add(entry)
        db_session.commit()

        assert entry.id is not None
        assert entry.color == "#4285f4"
        assert entry.is_primary is True
        assert len(entry.default_reminders) == 2

    def test_calendar_list_entry_unique_per_user_calendar(self, db_session):
        """Test that user can only have one entry per calendar."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        entry1 = CalendarListEntry(
            user_id=user.id, calendar_id=calendar.id, is_primary=True
        )
        db_session.add(entry1)
        db_session.commit()

        # Try to create another entry for same user-calendar pair
        entry2 = CalendarListEntry(
            user_id=user.id, calendar_id=calendar.id, is_primary=False
        )
        db_session.add(entry2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestReminderModel:
    """Test the Reminder model."""

    def test_create_reminder(self, db_session):
        """Test creating a reminder."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event = Event(
            calendar_id=calendar.id,
            summary="Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        db_session.add(event)
        db_session.flush()

        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=30
        )
        db_session.add(reminder)
        db_session.commit()

        assert reminder.id is not None
        assert reminder.method == ReminderMethod.POPUP
        assert reminder.minutes_before == 30


class TestModelRelationships:
    """Test relationships between models."""

    def test_user_calendars_relationship(self, db_session):
        """Test user can access owned calendars."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        cal1 = Calendar(title="Calendar 1", owner_id=user.id)
        cal2 = Calendar(title="Calendar 2", owner_id=user.id)
        db_session.add_all([cal1, cal2])
        db_session.commit()
        db_session.refresh(user)

        assert len(user.owned_calendars) == 2
        assert cal1 in user.owned_calendars
        assert cal2 in user.owned_calendars

    def test_calendar_events_relationship(self, db_session):
        """Test calendar can access events."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event1 = Event(
            calendar_id=calendar.id,
            summary="Event 1",
            start=now,
            end=now + timedelta(hours=1),
        )
        event2 = Event(
            calendar_id=calendar.id,
            summary="Event 2",
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=1),
        )
        db_session.add_all([event1, event2])
        db_session.commit()
        db_session.refresh(calendar)

        assert len(calendar.events) == 2
        assert event1 in calendar.events
        assert event2 in calendar.events

    def test_event_attendees_relationship(self, db_session):
        """Test event can access attendees."""
        user = User(email="user@example.com")
        db_session.add(user)
        db_session.flush()

        calendar = Calendar(title="Test", owner_id=user.id)
        db_session.add(calendar)
        db_session.flush()

        now = datetime.now(timezone.utc)
        event = Event(
            calendar_id=calendar.id,
            summary="Meeting",
            start=now,
            end=now + timedelta(hours=1),
        )
        db_session.add(event)
        db_session.flush()

        attendee1 = EventAttendee(event_id=event.id, email="attendee1@example.com")
        attendee2 = EventAttendee(event_id=event.id, email="attendee2@example.com")
        db_session.add_all([attendee1, attendee2])
        db_session.commit()
        db_session.refresh(event)

        assert len(event.attendees) == 2
        assert attendee1 in event.attendees
        assert attendee2 in event.attendees
