"""
Tests for attendee response functionality.

This module tests:
- Attendee response status updates (accept, decline, tentative)
- Notification logging when responses change
- Organizer notifications
- Recurring event responses
"""

import pytest
from datetime import datetime, timezone
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
    EventAttendee,
    NotificationLog,
    AttendeeResponseStatus,
    EventStatus,
)


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_attendee.db"
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
def test_users(db):
    """Create test users: organizer and two attendees."""
    organizer = User(
        id=uuid4(),
        email="organizer@example.com",
        name="Event Organizer",
    )
    attendee1 = User(
        id=uuid4(),
        email="attendee1@example.com",
        name="Attendee One",
    )
    attendee2 = User(
        id=uuid4(),
        email="attendee2@example.com",
        name="Attendee Two",
    )

    db.add_all([organizer, attendee1, attendee2])
    db.commit()
    db.refresh(organizer)
    db.refresh(attendee1)
    db.refresh(attendee2)

    return {
        "organizer": organizer,
        "attendee1": attendee1,
        "attendee2": attendee2,
    }


@pytest.fixture
def test_calendar(db, test_users):
    """Create a test calendar owned by the organizer."""
    calendar = Calendar(
        id=uuid4(),
        title="Test Calendar",
        timezone="UTC",
        owner_id=test_users["organizer"].id,
    )
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


@pytest.fixture
def test_event(db, test_calendar, test_users):
    """Create a test event with attendees."""
    event = Event(
        id=uuid4(),
        calendar_id=test_calendar.id,
        summary="Team Meeting",
        description="Weekly sync",
        start=datetime(2025, 11, 20, 10, 0, 0, tzinfo=timezone.utc),
        end=datetime(2025, 11, 20, 11, 0, 0, tzinfo=timezone.utc),
        status=EventStatus.CONFIRMED,
        organizer_id=test_users["organizer"].id,
        creator_id=test_users["organizer"].id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Add attendees
    attendee1 = EventAttendee(
        event_id=event.id,
        user_id=test_users["attendee1"].id,
        email=test_users["attendee1"].email,
        display_name=test_users["attendee1"].name,
        response_status=AttendeeResponseStatus.NEEDS_ACTION,
    )
    attendee2 = EventAttendee(
        event_id=event.id,
        user_id=test_users["attendee2"].id,
        email=test_users["attendee2"].email,
        display_name=test_users["attendee2"].name,
        response_status=AttendeeResponseStatus.NEEDS_ACTION,
    )
    db.add_all([attendee1, attendee2])
    db.commit()

    return event


class TestAttendeeResponses:
    """Test attendee response functionality."""

    def test_accept_event(self, db, test_event, test_users):
        """Test that an attendee can accept an event invitation."""
        response = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "accepted"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response_status"] == "accepted"
        assert data["email"] == test_users["attendee1"].email

        # Verify in database
        attendee = (
            db.query(EventAttendee)
            .filter(
                EventAttendee.event_id == test_event.id,
                EventAttendee.email == test_users["attendee1"].email,
            )
            .first()
        )
        assert attendee.response_status == AttendeeResponseStatus.ACCEPTED

    def test_decline_event(self, db, test_event, test_users):
        """Test that an attendee can decline an event invitation."""
        response = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee2'].email}",
            json={"response_status": "declined"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response_status"] == "declined"

    def test_tentative_response(self, db, test_event, test_users):
        """Test that an attendee can respond tentatively."""
        response = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "tentative"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response_status"] == "tentative"

    def test_notification_on_response(self, db, test_event, test_users):
        """Test that a notification is created when response status changes."""
        # Initially, no notifications
        initial_count = db.query(NotificationLog).count()

        # Attendee declines
        response = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "declined"},
        )

        assert response.status_code == 200

        # Check notification was created
        notifications = db.query(NotificationLog).all()
        assert len(notifications) == initial_count + 1

        # Verify notification details
        notification = notifications[-1]
        assert notification.event_id == test_event.id
        assert notification.user_id == test_users["organizer"].id
        assert "declined" in notification.message.lower()
        assert test_users["attendee1"].name in notification.message

    def test_attendee_not_found(self, db, test_event):
        """Test that responding as a non-existent attendee returns 404."""
        response = client.patch(
            f"/api/events/{test_event.id}/respond?user_email=nonexistent@example.com",
            json={"response_status": "accepted"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_event_not_found(self, db, test_users):
        """Test that responding to a non-existent event returns 404."""
        fake_event_id = uuid4()
        response = client.patch(
            f"/api/events/{fake_event_id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "accepted"},
        )

        assert response.status_code == 404

    def test_multiple_attendees_respond(self, db, test_event, test_users):
        """Test that multiple attendees can respond independently."""
        # Attendee 1 accepts
        response1 = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "accepted"},
        )
        assert response1.status_code == 200

        # Attendee 2 declines
        response2 = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee2'].email}",
            json={"response_status": "declined"},
        )
        assert response2.status_code == 200

        # Verify both responses in database
        attendees = (
            db.query(EventAttendee)
            .filter(EventAttendee.event_id == test_event.id)
            .all()
        )

        responses = {a.email: a.response_status for a in attendees}
        assert (
            responses[test_users["attendee1"].email] == AttendeeResponseStatus.ACCEPTED
        )
        assert (
            responses[test_users["attendee2"].email] == AttendeeResponseStatus.DECLINED
        )

    def test_change_response(self, db, test_event, test_users):
        """Test that an attendee can change their response."""
        # First accept
        response1 = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "accepted"},
        )
        assert response1.status_code == 200
        assert response1.json()["response_status"] == "accepted"

        # Then change to declined
        response2 = client.patch(
            f"/api/events/{test_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "declined"},
        )
        assert response2.status_code == 200
        assert response2.json()["response_status"] == "declined"

        # Verify final status
        attendee = (
            db.query(EventAttendee)
            .filter(
                EventAttendee.event_id == test_event.id,
                EventAttendee.email == test_users["attendee1"].email,
            )
            .first()
        )
        assert attendee.response_status == AttendeeResponseStatus.DECLINED


class TestRecurringEventResponses:
    """Test attendee responses for recurring events."""

    def test_decline_recurring_instance_notifies_organizer(
        self, db, test_calendar, test_users
    ):
        """
        Test that declining a recurring event instance creates a notification
        for the organizer.

        This is the key test requested: one user declines recurring instance
        → check organizer update.
        """
        # Create a recurring event
        recurring_event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Weekly Standup",
            description="Every Monday",
            start=datetime(2025, 11, 17, 9, 0, 0, tzinfo=timezone.utc),  # Monday
            end=datetime(2025, 11, 17, 9, 30, 0, tzinfo=timezone.utc),
            status=EventStatus.CONFIRMED,
            organizer_id=test_users["organizer"].id,
            creator_id=test_users["organizer"].id,
            recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=4"],  # 4 weeks
        )
        db.add(recurring_event)
        db.commit()
        db.refresh(recurring_event)

        # Add attendee to the recurring event
        attendee = EventAttendee(
            event_id=recurring_event.id,
            user_id=test_users["attendee1"].id,
            email=test_users["attendee1"].email,
            display_name=test_users["attendee1"].name,
            response_status=AttendeeResponseStatus.NEEDS_ACTION,
        )
        db.add(attendee)
        db.commit()

        # Attendee declines the recurring event
        response = client.patch(
            f"/api/events/{recurring_event.id}/respond?user_email={test_users['attendee1'].email}",
            json={"response_status": "declined"},
        )

        assert response.status_code == 200
        assert response.json()["response_status"] == "declined"

        # Verify organizer notification was created
        notifications = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.event_id == recurring_event.id,
                NotificationLog.user_id == test_users["organizer"].id,
            )
            .all()
        )

        assert len(notifications) == 1
        notification = notifications[0]

        # Verify notification content
        assert notification.event_id == recurring_event.id
        assert notification.user_id == test_users["organizer"].id
        assert "declined" in notification.message.lower()
        assert "Weekly Standup" in notification.message
        assert test_users["attendee1"].name in notification.message

        # Verify notification metadata
        assert notification.event_summary == "Weekly Standup"
        assert notification.event_start == recurring_event.start

    def test_accept_recurring_event(self, db, test_calendar, test_users):
        """Test that accepting a recurring event works correctly."""
        # Create a recurring event
        recurring_event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            summary="Daily Sync",
            start=datetime(2025, 11, 17, 10, 0, 0, tzinfo=timezone.utc),
            end=datetime(2025, 11, 17, 10, 15, 0, tzinfo=timezone.utc),
            status=EventStatus.CONFIRMED,
            organizer_id=test_users["organizer"].id,
            recurrence=["RRULE:FREQ=DAILY;COUNT=5"],
        )
        db.add(recurring_event)
        db.commit()

        # Add attendee
        attendee = EventAttendee(
            event_id=recurring_event.id,
            user_id=test_users["attendee2"].id,
            email=test_users["attendee2"].email,
            display_name=test_users["attendee2"].name,
            response_status=AttendeeResponseStatus.NEEDS_ACTION,
        )
        db.add(attendee)
        db.commit()

        # Attendee accepts
        response = client.patch(
            f"/api/events/{recurring_event.id}/respond?user_email={test_users['attendee2'].email}",
            json={"response_status": "accepted"},
        )

        assert response.status_code == 200

        # Verify acceptance
        updated_attendee = (
            db.query(EventAttendee)
            .filter(
                EventAttendee.event_id == recurring_event.id,
                EventAttendee.email == test_users["attendee2"].email,
            )
            .first()
        )
        assert updated_attendee.response_status == AttendeeResponseStatus.ACCEPTED

        # Verify organizer was notified
        notification = (
            db.query(NotificationLog)
            .filter(NotificationLog.event_id == recurring_event.id)
            .first()
        )
        assert notification is not None
        assert "accepted" in notification.message.lower()
