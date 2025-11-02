"""
Unit tests for event propagation and attendee management.

Tests cover:
- Organizer creates event with attendees → attendee copies are created
- Attendee accepts invitation → organizer's event is updated
- Organizer updates event → all attendee copies are updated
- Multiple attendees and their responses
- iCalUID linking between organizer and attendee copies
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from datetime import datetime, timezone

from app.db import Base
from app.models.models import (
    User,
    Calendar,
    Event,
    EventAttendee,
    CalendarListEntry,
    AttendeeResponseStatus,
    EventStatus,
)
from app.services.event_service import (
    create_event,
    update_event,
    update_attendee_response,
    get_all_event_copies,
    get_event_by_ical_uid,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_users(db_session: Session):
    """Create test users for organizer and attendees."""
    users = {
        "organizer": User(
            id=uuid4(), email="organizer@example.com", name="Event Organizer"
        ),
        "alice": User(id=uuid4(), email="alice@example.com", name="Alice Smith"),
        "bob": User(id=uuid4(), email="bob@example.com", name="Bob Jones"),
        "charlie": User(id=uuid4(), email="charlie@example.com", name="Charlie Brown"),
    }

    for user in users.values():
        db_session.add(user)

    db_session.commit()

    for user in users.values():
        db_session.refresh(user)

    return users


@pytest.fixture
def organizer_calendar(db_session: Session, test_users):
    """Create a calendar for the organizer."""
    calendar = Calendar(
        id=uuid4(),
        title="Organizer's Calendar",
        timezone="UTC",
        owner_id=test_users["organizer"].id,
        description="Primary calendar",
    )

    db_session.add(calendar)
    db_session.commit()
    db_session.refresh(calendar)

    # Create calendar list entry
    list_entry = CalendarListEntry(
        user_id=test_users["organizer"].id, calendar_id=calendar.id, is_primary=True
    )
    db_session.add(list_entry)
    db_session.commit()

    return calendar


class TestCreateEventWithAttendees:
    """Test event creation with attendee propagation."""

    def test_create_event_without_attendees(
        self, db_session, test_users, organizer_calendar
    ):
        """Test creating a simple event without attendees."""
        payload = {
            "summary": "Solo Meeting",
            "start": datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
            "description": "A meeting with no attendees",
            "location": "Office",
        }

        event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        assert event.summary == "Solo Meeting"
        assert event.calendar_id == organizer_calendar.id
        assert event.iCalUID is not None
        assert len(event.attendees) == 1  # Only organizer
        assert event.attendees[0].email == test_users["organizer"].email
        assert event.attendees[0].is_organizer is True

    def test_create_event_with_attendees_creates_copies(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that creating event with attendees creates copies in their calendars."""
        payload = {
            "summary": "Team Meeting",
            "start": datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
            "description": "Weekly team sync",
            "attendees": [
                {"email": "alice@example.com", "display_name": "Alice"},
                {"email": "bob@example.com", "display_name": "Bob"},
            ],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Verify organizer's event
        assert organizer_event.summary == "Team Meeting"
        assert organizer_event.iCalUID is not None
        assert len(organizer_event.attendees) == 3  # Organizer + 2 attendees

        # Verify all event copies exist with same iCalUID
        all_copies = get_all_event_copies(db_session, organizer_event.iCalUID)
        assert len(all_copies) == 3  # Organizer + Alice + Bob

        # Verify each attendee has a copy
        alice_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["alice"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )
        assert alice_calendar is not None

        alice_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, alice_calendar.calendar_id
        )
        assert alice_event is not None
        assert alice_event.summary == "Team Meeting"
        assert len(alice_event.attendees) == 3

    def test_event_copies_have_same_ical_uid(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that all event copies share the same iCalUID."""
        payload = {
            "summary": "Sync Meeting",
            "start": datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
            "attendees": [
                {"email": "alice@example.com"},
                {"email": "bob@example.com"},
                {"email": "charlie@example.com"},
            ],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        ical_uid = organizer_event.iCalUID
        all_copies = get_all_event_copies(db_session, ical_uid)

        # All copies should have the same iCalUID
        for event in all_copies:
            assert event.iCalUID == ical_uid

    def test_attendee_copies_include_all_attendees(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that attendee copies include the full attendee list."""
        payload = {
            "summary": "All Hands",
            "start": datetime(2025, 1, 20, 9, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 20, 10, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}, {"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Get Alice's copy
        alice_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["alice"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )

        alice_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, alice_calendar.calendar_id
        )

        # Alice's copy should have all attendees (organizer + alice + bob)
        assert len(alice_event.attendees) == 3

        attendee_emails = {att.email for att in alice_event.attendees}
        assert "organizer@example.com" in attendee_emails
        assert "alice@example.com" in attendee_emails
        assert "bob@example.com" in attendee_emails

    def test_organizer_marked_as_accepted(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that organizer is automatically marked as ACCEPTED."""
        payload = {
            "summary": "Project Kickoff",
            "start": datetime(2025, 1, 25, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 25, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Find organizer attendee record
        organizer_attendee = next(
            (att for att in organizer_event.attendees if att.is_organizer), None
        )

        assert organizer_attendee is not None
        assert organizer_attendee.response_status == AttendeeResponseStatus.ACCEPTED

    def test_attendees_marked_as_needs_action(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that invited attendees are marked as NEEDS_ACTION."""
        payload = {
            "summary": "Review Session",
            "start": datetime(2025, 1, 30, 14, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 30, 15, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}, {"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Check that non-organizer attendees have NEEDS_ACTION status
        for attendee in organizer_event.attendees:
            if not attendee.is_organizer:
                assert attendee.response_status == AttendeeResponseStatus.NEEDS_ACTION


class TestAttendeeResponse:
    """Test attendee response propagation."""

    def test_attendee_accept_updates_organizer(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that attendee accepting invitation updates organizer's event."""
        # Create event with attendee
        payload = {
            "summary": "Important Meeting",
            "start": datetime(2025, 2, 1, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 2, 1, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Get Alice's event copy
        alice_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["alice"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )

        alice_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, alice_calendar.calendar_id
        )

        # Alice accepts the invitation
        update_attendee_response(
            db_session,
            alice_event.id,
            "alice@example.com",
            AttendeeResponseStatus.ACCEPTED,
        )

        # Refresh organizer's event
        db_session.refresh(organizer_event)

        # Check that Alice's response is updated on organizer's event
        alice_on_organizer = next(
            (
                att
                for att in organizer_event.attendees
                if att.email == "alice@example.com"
            ),
            None,
        )

        assert alice_on_organizer is not None
        assert alice_on_organizer.response_status == AttendeeResponseStatus.ACCEPTED

    def test_attendee_decline_updates_organizer(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that attendee declining invitation updates organizer's event."""
        payload = {
            "summary": "Optional Meeting",
            "start": datetime(2025, 2, 5, 15, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 2, 5, 16, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Get Bob's event copy
        bob_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["bob"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )

        bob_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, bob_calendar.calendar_id
        )

        # Bob declines
        update_attendee_response(
            db_session, bob_event.id, "bob@example.com", AttendeeResponseStatus.DECLINED
        )

        # Refresh organizer's event
        db_session.refresh(organizer_event)

        bob_on_organizer = next(
            (
                att
                for att in organizer_event.attendees
                if att.email == "bob@example.com"
            ),
            None,
        )

        assert bob_on_organizer is not None
        assert bob_on_organizer.response_status == AttendeeResponseStatus.DECLINED

    def test_multiple_attendee_responses(
        self, db_session, test_users, organizer_calendar
    ):
        """Test multiple attendees responding with different statuses."""
        payload = {
            "summary": "Multi-Attendee Meeting",
            "start": datetime(2025, 2, 10, 11, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 2, 10, 12, 0, tzinfo=timezone.utc),
            "attendees": [
                {"email": "alice@example.com"},
                {"email": "bob@example.com"},
                {"email": "charlie@example.com"},
            ],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Get each attendee's event copy
        for user_key, status in [
            ("alice", AttendeeResponseStatus.ACCEPTED),
            ("bob", AttendeeResponseStatus.DECLINED),
            ("charlie", AttendeeResponseStatus.TENTATIVE),
        ]:
            user = test_users[user_key]
            calendar_entry = (
                db_session.query(CalendarListEntry)
                .filter(
                    CalendarListEntry.user_id == user.id,
                    CalendarListEntry.is_primary == True,
                )
                .first()
            )

            user_event = get_event_by_ical_uid(
                db_session, organizer_event.iCalUID, calendar_entry.calendar_id
            )

            update_attendee_response(db_session, user_event.id, user.email, status)

        # Refresh organizer's event
        db_session.refresh(organizer_event)

        # Verify all responses are updated on organizer's event
        response_map = {
            att.email: att.response_status for att in organizer_event.attendees
        }

        assert response_map["alice@example.com"] == AttendeeResponseStatus.ACCEPTED
        assert response_map["bob@example.com"] == AttendeeResponseStatus.DECLINED
        assert response_map["charlie@example.com"] == AttendeeResponseStatus.TENTATIVE

    def test_attendee_response_propagates_to_all_copies(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that attendee response is visible on all event copies."""
        payload = {
            "summary": "Three Person Meeting",
            "start": datetime(2025, 2, 15, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 2, 15, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}, {"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Alice accepts
        alice_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["alice"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )

        alice_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, alice_calendar.calendar_id
        )

        update_attendee_response(
            db_session,
            alice_event.id,
            "alice@example.com",
            AttendeeResponseStatus.ACCEPTED,
        )

        # Get Bob's copy and check if Alice's response is visible
        bob_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["bob"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )

        bob_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, bob_calendar.calendar_id
        )

        alice_on_bob_event = next(
            (att for att in bob_event.attendees if att.email == "alice@example.com"),
            None,
        )

        assert alice_on_bob_event is not None
        assert alice_on_bob_event.response_status == AttendeeResponseStatus.ACCEPTED


class TestOrganizerUpdate:
    """Test organizer event update propagation."""

    def test_organizer_update_summary_propagates(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that updating event summary propagates to attendees."""
        payload = {
            "summary": "Original Title",
            "start": datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 3, 1, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Update the event
        update_event(db_session, organizer_event.id, {"summary": "Updated Title"})

        # Get Alice's copy
        alice_calendar = (
            db_session.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == test_users["alice"].id,
                CalendarListEntry.is_primary == True,
            )
            .first()
        )

        alice_event = get_event_by_ical_uid(
            db_session, organizer_event.iCalUID, alice_calendar.calendar_id
        )

        assert alice_event.summary == "Updated Title"

    def test_organizer_update_time_propagates(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that updating event time propagates to attendees."""
        payload = {
            "summary": "Time Change Test",
            "start": datetime(2025, 3, 5, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 3, 5, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}, {"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        new_start = datetime(2025, 3, 5, 14, 0, tzinfo=timezone.utc)
        new_end = datetime(2025, 3, 5, 15, 30, tzinfo=timezone.utc)

        # Update times
        update_event(
            db_session, organizer_event.id, {"start": new_start, "end": new_end}
        )

        # Verify all copies have updated times
        all_copies = get_all_event_copies(db_session, organizer_event.iCalUID)

        for event in all_copies:
            # SQLite doesn't preserve timezone info, so compare naive datetimes
            assert event.start == new_start.replace(tzinfo=None)
            assert event.end == new_end.replace(tzinfo=None)

    def test_organizer_update_location_propagates(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that updating event location propagates to attendees."""
        payload = {
            "summary": "Location Change",
            "start": datetime(2025, 3, 10, 9, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 3, 10, 10, 0, tzinfo=timezone.utc),
            "location": "Office A",
            "attendees": [{"email": "alice@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Update location
        update_event(db_session, organizer_event.id, {"location": "Conference Room B"})

        # Verify propagation
        all_copies = get_all_event_copies(db_session, organizer_event.iCalUID)

        for event in all_copies:
            assert event.location == "Conference Room B"

    def test_organizer_update_multiple_fields_propagates(
        self, db_session, test_users, organizer_calendar
    ):
        """Test updating multiple fields at once propagates correctly."""
        payload = {
            "summary": "Multi-Field Update",
            "start": datetime(2025, 3, 15, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 3, 15, 11, 0, tzinfo=timezone.utc),
            "location": "Room 1",
            "description": "Original description",
            "attendees": [{"email": "alice@example.com"}, {"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Update multiple fields
        updates = {
            "summary": "Updated Multi-Field",
            "location": "Room 2",
            "description": "Updated description",
            "start": datetime(2025, 3, 15, 11, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 3, 15, 12, 30, tzinfo=timezone.utc),
        }

        update_event(db_session, organizer_event.id, updates)

        # Verify all copies have all updates
        all_copies = get_all_event_copies(db_session, organizer_event.iCalUID)

        for event in all_copies:
            assert event.summary == "Updated Multi-Field"
            assert event.location == "Room 2"
            assert event.description == "Updated description"
            # SQLite doesn't preserve timezone info, so compare naive datetimes
            assert event.start == datetime(2025, 3, 15, 11, 0)
            assert event.end == datetime(2025, 3, 15, 12, 30)

    def test_organizer_cancel_event_propagates(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that cancelling an event propagates to all attendees."""
        payload = {
            "summary": "Cancellable Meeting",
            "start": datetime(2025, 3, 20, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 3, 20, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}, {"email": "bob@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        # Cancel the event
        update_event(db_session, organizer_event.id, {"status": EventStatus.CANCELLED})

        # Verify all copies are cancelled
        all_copies = get_all_event_copies(db_session, organizer_event.iCalUID)

        for event in all_copies:
            assert event.status == EventStatus.CANCELLED


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_update_nonexistent_event_raises_error(self, db_session):
        """Test that updating non-existent event raises error."""
        fake_event_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            update_event(db_session, fake_event_id, {"summary": "New Title"})

    def test_update_attendee_response_nonexistent_event_raises_error(self, db_session):
        """Test that updating response on non-existent event raises error."""
        fake_event_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            update_attendee_response(
                db_session,
                fake_event_id,
                "test@example.com",
                AttendeeResponseStatus.ACCEPTED,
            )

    def test_update_attendee_response_nonexistent_attendee_raises_error(
        self, db_session, test_users, organizer_calendar
    ):
        """Test that updating response for non-existent attendee raises error."""
        payload = {
            "summary": "Test Event",
            "start": datetime(2025, 4, 1, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 4, 1, 11, 0, tzinfo=timezone.utc),
            "attendees": [{"email": "alice@example.com"}],
        }

        organizer_event = create_event(
            db_session, organizer_calendar.id, test_users["organizer"].email, payload
        )

        with pytest.raises(ValueError, match="not found"):
            update_attendee_response(
                db_session,
                organizer_event.id,
                "nonexistent@example.com",
                AttendeeResponseStatus.ACCEPTED,
            )

    def test_event_without_ical_uid_cannot_be_updated(
        self, db_session, organizer_calendar
    ):
        """Test that events without iCalUID cannot use propagation."""
        # Create event directly without using create_event
        event = Event(
            id=uuid4(),
            calendar_id=organizer_calendar.id,
            summary="No iCalUID Event",
            start=datetime(2025, 4, 5, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 4, 5, 11, 0, tzinfo=timezone.utc),
            iCalUID=None,  # No iCalUID
        )

        db_session.add(event)
        db_session.commit()

        with pytest.raises(ValueError, match="no iCalUID"):
            update_event(db_session, event.id, {"summary": "Updated"})
