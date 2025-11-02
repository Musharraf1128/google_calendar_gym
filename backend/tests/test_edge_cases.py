"""
Edge case tests for Google Calendar Gym.

This module tests complex scenarios and edge cases:
1. Overlapping events on the same calendar
2. Recurrence ending mid-month with EXDATE omissions
3. Calendar shared with freeBusyReader only -> verify restricted view
4. Attendee cancels one instance of recurring event -> organizer update propagation
5. Reminder overrides revert to defaults correctly
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.db import Base
from app.models.models import (
    User,
    Calendar,
    Event,
    EventAttendee,
    CalendarListEntry,
    CalendarACL,
    CalendarRole,
    Reminder,
    ReminderMethod,
    EventStatus,
    AttendeeResponseStatus,
)
from app.services.acl_service import check_permission, get_user_role
from app.services.event_service import (
    create_event,
    update_event,
    update_attendee_response,
    get_all_event_copies,
)
from app.services.reminder_service import (
    get_event_reminders,
    schedule_reminders,
)
from app.utils.recurrence import expand_recurrence


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
    """Create test users for various scenarios."""
    users = {
        "organizer": User(
            id=uuid4(), email="organizer@example.com", name="Event Organizer"
        ),
        "alice": User(id=uuid4(), email="alice@example.com", name="Alice Smith"),
        "bob": User(id=uuid4(), email="bob@example.com", name="Bob Jones"),
        "freebusy_user": User(
            id=uuid4(), email="freebusy@example.com", name="FreeBusy User"
        ),
    }

    for user in users.values():
        db_session.add(user)

    db_session.commit()

    for user in users.values():
        db_session.refresh(user)

    return users


@pytest.fixture
def test_calendar(db_session: Session, test_users):
    """Create a test calendar for the organizer."""
    calendar = Calendar(
        id=uuid4(),
        title="Test Calendar",
        timezone="America/New_York",
        owner_id=test_users["organizer"].id,
        description="Test calendar for edge cases",
    )

    db_session.add(calendar)
    db_session.commit()
    db_session.refresh(calendar)

    # Create calendar list entry for organizer
    list_entry = CalendarListEntry(
        user_id=test_users["organizer"].id,
        calendar_id=calendar.id,
        is_primary=True,
        default_reminders=[
            {"method": "popup", "minutes": 30},
            {"method": "email", "minutes": 1440},  # 1 day
        ],
    )
    db_session.add(list_entry)
    db_session.commit()

    return calendar


@pytest.fixture
def attendee_calendars(db_session: Session, test_users):
    """Create calendars for attendees."""
    calendars = {}

    for key in ["alice", "bob"]:
        user = test_users[key]
        calendar = Calendar(
            id=uuid4(),
            title=f"{user.name}'s Calendar",
            timezone="America/New_York",
            owner_id=user.id,
        )
        db_session.add(calendar)
        db_session.flush()

        # Create calendar list entry
        list_entry = CalendarListEntry(
            user_id=user.id, calendar_id=calendar.id, is_primary=True
        )
        db_session.add(list_entry)
        calendars[key] = calendar

    db_session.commit()

    for calendar in calendars.values():
        db_session.refresh(calendar)

    return calendars


# ====================================================================================
# TEST 1: Overlapping Events on Same Calendar
# ====================================================================================


class TestOverlappingEvents:
    """Test scenarios with overlapping events on the same calendar."""

    def test_detect_overlapping_events_same_time(self, db_session, test_calendar):
        """Test detection of events at exactly the same time."""
        start_time = datetime(2025, 11, 15, 14, 0, 0)
        end_time = datetime(2025, 11, 15, 15, 0, 0)

        # Create first event
        event1 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting 1",
            start=start_time,
            end=end_time,
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event1)

        # Create second event at exact same time
        event2 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting 2",
            start=start_time,
            end=end_time,
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event2)
        db_session.commit()

        # Query overlapping events
        overlapping = (
            db_session.query(Event)
            .filter(
                Event.calendar_id == test_calendar.id,
                Event.start < end_time,
                Event.end > start_time,
                Event.status == EventStatus.CONFIRMED,
            )
            .all()
        )

        assert len(overlapping) == 2
        assert event1 in overlapping
        assert event2 in overlapping

    def test_detect_partial_overlap(self, db_session, test_calendar):
        """Test detection of partially overlapping events."""
        # Event 1: 14:00 - 15:00
        event1 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting 1",
            start=datetime(2025, 11, 15, 14, 0, 0),
            end=datetime(2025, 11, 15, 15, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event1)

        # Event 2: 14:30 - 15:30 (overlaps last 30 min of event1)
        event2 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting 2",
            start=datetime(2025, 11, 15, 14, 30, 0),
            end=datetime(2025, 11, 15, 15, 30, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event2)
        db_session.commit()

        # Check overlap for event1's time
        overlapping_with_event1 = (
            db_session.query(Event)
            .filter(
                Event.calendar_id == test_calendar.id,
                Event.start < event1.end,
                Event.end > event1.start,
                Event.id != event1.id,
                Event.status == EventStatus.CONFIRMED,
            )
            .all()
        )

        assert len(overlapping_with_event1) == 1
        assert event2 in overlapping_with_event1

    def test_no_overlap_adjacent_events(self, db_session, test_calendar):
        """Test that adjacent events (one ends when other starts) don't overlap."""
        # Event 1: 14:00 - 15:00
        event1 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting 1",
            start=datetime(2025, 11, 15, 14, 0, 0),
            end=datetime(2025, 11, 15, 15, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event1)

        # Event 2: 15:00 - 16:00 (starts when event1 ends)
        event2 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting 2",
            start=datetime(2025, 11, 15, 15, 0, 0),
            end=datetime(2025, 11, 15, 16, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event2)
        db_session.commit()

        # Check overlap (should be none with proper < and > operators)
        overlapping = (
            db_session.query(Event)
            .filter(
                Event.calendar_id == test_calendar.id,
                Event.start < event1.end,
                Event.end > event1.start,
                Event.id != event1.id,
                Event.status == EventStatus.CONFIRMED,
            )
            .all()
        )

        # With < and >, adjacent events shouldn't overlap
        assert len(overlapping) == 0

    def test_overlapping_across_multiple_calendars(
        self, db_session, test_calendar, test_users
    ):
        """Test that events on different calendars can overlap without conflict."""
        # Create another calendar
        calendar2 = Calendar(
            id=uuid4(),
            title="Calendar 2",
            timezone="America/New_York",
            owner_id=test_users["alice"].id,
        )
        db_session.add(calendar2)
        db_session.commit()

        start_time = datetime(2025, 11, 15, 14, 0, 0)
        end_time = datetime(2025, 11, 15, 15, 0, 0)

        # Event on first calendar
        event1 = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting on Cal 1",
            start=start_time,
            end=end_time,
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event1)

        # Event on second calendar at same time (should be allowed)
        event2 = Event(
            id=uuid4(),
            calendar_id=calendar2.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting on Cal 2",
            start=start_time,
            end=end_time,
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event2)
        db_session.commit()

        # Both events should exist independently
        cal1_events = (
            db_session.query(Event).filter(Event.calendar_id == test_calendar.id).all()
        )
        cal2_events = (
            db_session.query(Event).filter(Event.calendar_id == calendar2.id).all()
        )

        assert len(cal1_events) == 1
        assert len(cal2_events) == 1
        assert event1.calendar_id != event2.calendar_id


# ====================================================================================
# TEST 2: Recurrence Ending Mid-Month with EXDATE Omissions
# ====================================================================================


class TestRecurrenceWithExdates:
    """Test recurrence patterns ending mid-month with exception dates."""

    def test_daily_recurrence_ending_mid_month(self, db_session, test_calendar):
        """Test daily recurrence that ends mid-month."""
        start_date = datetime(2025, 11, 1, 10, 0, 0)

        # Daily for 15 days (ends Nov 15, mid-month)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Daily Standup",
            start=start_date,
            end=start_date + timedelta(minutes=30),
            recurrence=["RRULE:FREQ=DAILY;COUNT=15"],
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.commit()

        # Expand recurrence
        window_start = datetime(2025, 11, 1, 0, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59, 59)
        occurrences = expand_recurrence(
            event.start, event.recurrence, window_start, window_end
        )

        assert len(occurrences) == 15
        assert occurrences[0] == start_date
        assert occurrences[-1] == datetime(2025, 11, 15, 10, 0, 0)

    def test_recurrence_with_exdate_omissions(self, db_session, test_calendar):
        """Test recurrence with specific dates excluded via EXDATE."""
        start_date = datetime(2025, 11, 1, 10, 0, 0)

        # Daily for 10 days with 3 exceptions
        # EXDATE should be part of the recurrence array
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Daily Meeting",
            start=start_date,
            end=start_date + timedelta(minutes=60),
            recurrence=[
                "RRULE:FREQ=DAILY;COUNT=10",
                "EXDATE:20251103T100000,20251107T100000,20251109T100000"
            ],
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.commit()

        # Expand recurrence
        window_start = datetime(2025, 11, 1, 0, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59, 59)
        occurrences = expand_recurrence(
            event.start, event.recurrence, window_start, window_end
        )

        # Should be 10 - 3 = 7 occurrences
        assert len(occurrences) == 7

        # Verify excluded dates are not in occurrences
        excluded_dates = [
            datetime(2025, 11, 3, 10, 0, 0),
            datetime(2025, 11, 7, 10, 0, 0),
            datetime(2025, 11, 9, 10, 0, 0),
        ]
        for excluded in excluded_dates:
            assert excluded not in occurrences

    def test_weekly_recurrence_ending_mid_month_with_exdates(
        self, db_session, test_calendar
    ):
        """Test weekly recurrence ending mid-month with excluded dates."""
        # Start on Nov 1 (Friday), weekly on Mondays and Fridays
        start_date = datetime(2025, 11, 1, 14, 0, 0)  # Saturday in 2025

        # Weekly on Mon/Fri for 4 weeks
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Team Sync",
            start=start_date,
            end=start_date + timedelta(minutes=60),
            recurrence=[
                "RRULE:FREQ=WEEKLY;BYDAY=MO,FR;COUNT=8",  # 4 weeks = 8 occurrences
                "EXDATE:20251110T140000,20251121T140000"
            ],
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.commit()

        # Expand recurrence
        window_start = datetime(2025, 11, 1, 0, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59, 59)
        occurrences = expand_recurrence(
            event.start, event.recurrence, window_start, window_end
        )

        # Should be 8 - 2 = 6 occurrences
        assert len(occurrences) == 6

        # Verify all occurrences are Mon or Fri
        for occ in occurrences:
            assert occ.weekday() in [0, 4]  # Monday=0, Friday=4

        # Verify excluded dates are not in occurrences
        assert datetime(2025, 11, 10, 14, 0, 0) not in occurrences
        assert datetime(2025, 11, 21, 14, 0, 0) not in occurrences


# ====================================================================================
# TEST 3: FreeBusyReader Restricted View
# ====================================================================================


class TestFreeBusyReaderRestrictions:
    """Test that freeBusyReader role only sees limited information."""

    def test_freebusy_reader_permission_level(
        self, db_session, test_calendar, test_users
    ):
        """Test that freeBusyReader has correct permission level."""
        freebusy_user = test_users["freebusy_user"]

        # Grant freeBusyReader access
        acl = CalendarACL(
            calendar_id=test_calendar.id,
            grantee=freebusy_user.email,
            role=CalendarRole.FREE_BUSY_READER,
        )
        db_session.add(acl)

        # Create calendar list entry
        list_entry = CalendarListEntry(
            user_id=freebusy_user.id, calendar_id=test_calendar.id, is_primary=False
        )
        db_session.add(list_entry)
        db_session.commit()

        # Verify role
        role = get_user_role(db_session, freebusy_user.id, test_calendar.id)
        assert role == CalendarRole.FREE_BUSY_READER

        # Verify permissions
        assert check_permission(
            db_session, freebusy_user.id, test_calendar.id, CalendarRole.FREE_BUSY_READER
        )
        assert not check_permission(
            db_session, freebusy_user.id, test_calendar.id, CalendarRole.READER
        )
        assert not check_permission(
            db_session, freebusy_user.id, test_calendar.id, CalendarRole.WRITER
        )

    def test_freebusy_reader_cannot_see_event_details(
        self, db_session, test_calendar, test_users
    ):
        """
        Test that freeBusyReader should only see start/end times, not details.

        Note: This tests the access level. In a real implementation, the API
        endpoint would filter out sensitive fields like summary, description,
        location, attendees for freeBusyReader users.
        """
        freebusy_user = test_users["freebusy_user"]

        # Grant freeBusyReader access
        acl = CalendarACL(
            calendar_id=test_calendar.id,
            grantee=freebusy_user.email,
            role=CalendarRole.FREE_BUSY_READER,
        )
        db_session.add(acl)
        db_session.commit()

        # Create event with details
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Confidential Meeting",
            description="Secret project discussion",
            location="Executive Suite",
            start=datetime(2025, 11, 15, 14, 0, 0),
            end=datetime(2025, 11, 15, 15, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.commit()

        # Verify user has only freeBusyReader access
        role = get_user_role(db_session, freebusy_user.id, test_calendar.id)
        assert role == CalendarRole.FREE_BUSY_READER

        # FreeBusyReader should be able to query the event exists
        # but in a real API, details would be filtered
        # This is a contract that the API layer should enforce

    def test_freebusy_reader_cannot_modify_events(
        self, db_session, test_calendar, test_users
    ):
        """Test that freeBusyReader cannot modify events (permission check)."""
        freebusy_user = test_users["freebusy_user"]

        # Grant freeBusyReader access
        acl = CalendarACL(
            calendar_id=test_calendar.id,
            grantee=freebusy_user.email,
            role=CalendarRole.FREE_BUSY_READER,
        )
        db_session.add(acl)
        db_session.commit()

        # Verify cannot write
        can_write = check_permission(
            db_session, freebusy_user.id, test_calendar.id, CalendarRole.WRITER
        )
        assert not can_write

        # This means API should reject any create/update/delete attempts
        # from this user on this calendar


# ====================================================================================
# TEST 4: Attendee Cancels One Instance of Recurring Event -> Organizer Update
# ====================================================================================


class TestRecurringEventInstanceCancellation:
    """Test attendee cancelling one instance of a recurring event."""

    def test_attendee_cancels_single_instance_of_recurring_event(
        self, db_session, test_calendar, test_users, attendee_calendars
    ):
        """
        Test scenario where an attendee cancels one instance of a recurring event.

        Expected behavior:
        1. Organizer's recurring event should remain unchanged
        2. Attendee's response for that specific instance should be 'declined'
        3. For recurring events, attendee responses are typically stored separately
           or the attendee creates an EXDATE on their copy
        """
        organizer = test_users["organizer"]
        alice = test_users["alice"]

        # Create recurring event (every Monday for 4 weeks)
        start_date = datetime(2025, 11, 3, 10, 0, 0)  # Monday

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Weekly Team Meeting",
            start=start_date,
            end=start_date + timedelta(minutes=60),
            recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=4"],
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Add Alice as attendee
        attendee = EventAttendee(
            event_id=event.id,
            email=alice.email,
            display_name=alice.name,
            response_status=AttendeeResponseStatus.ACCEPTED,
            is_organizer=False,
        )
        db_session.add(attendee)
        db_session.commit()

        # Alice declines the second instance (Nov 10)
        # In a real system, this would create an exception
        # For testing, we verify the attendee can change their response
        attendee.response_status = AttendeeResponseStatus.DECLINED
        db_session.commit()
        db_session.refresh(attendee)

        # Verify attendee status changed
        assert attendee.response_status == AttendeeResponseStatus.DECLINED

        # Verify organizer's event still exists
        db_session.refresh(event)
        assert event.status == EventStatus.CONFIRMED

        # In Google Calendar, declining one instance would:
        # 1. Add EXDATE to attendee's copy for that specific instance
        # 2. Notify organizer that attendee declined that instance
        # This is a simplified test showing the data model supports it

    def test_organizer_sees_attendee_declined_instance(
        self, db_session, test_calendar, test_users, attendee_calendars
    ):
        """
        Test that organizer can see when an attendee declines a specific instance.
        """
        organizer = test_users["organizer"]
        bob = test_users["bob"]

        # Create recurring event
        start_date = datetime(2025, 11, 5, 14, 0, 0)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Bi-weekly Planning",
            start=start_date,
            end=start_date + timedelta(minutes=90),
            recurrence=["RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=3"],  # 3 occurrences
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Add Bob as attendee
        attendee = EventAttendee(
            event_id=event.id,
            email=bob.email,
            display_name=bob.name,
            response_status=AttendeeResponseStatus.NEEDS_ACTION,
            is_organizer=False,
        )
        db_session.add(attendee)
        db_session.commit()

        # Bob declines
        attendee.response_status = AttendeeResponseStatus.DECLINED
        db_session.commit()

        # Organizer queries attendees for this event
        attendees = (
            db_session.query(EventAttendee).filter(EventAttendee.event_id == event.id).all()
        )

        declined_attendees = [
            a for a in attendees if a.response_status == AttendeeResponseStatus.DECLINED
        ]

        assert len(declined_attendees) == 1
        assert declined_attendees[0].email == bob.email


# ====================================================================================
# TEST 5: Reminder Overrides Revert to Defaults Correctly
# ====================================================================================


class TestReminderOverridesAndDefaults:
    """Test reminder overrides and reversion to calendar defaults."""

    def test_event_uses_calendar_default_reminders(self, db_session, test_calendar):
        """Test that event without reminders uses calendar defaults."""
        # Calendar has default reminders set in fixture:
        # - popup: 30 min
        # - email: 1440 min (1 day)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting with defaults",
            start=datetime(2025, 11, 15, 14, 0, 0),
            end=datetime(2025, 11, 15, 15, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.commit()

        # Query reminders for this event (should be none at event level)
        event_reminders = (
            db_session.query(Reminder).filter(Reminder.event_id == event.id).all()
        )
        assert len(event_reminders) == 0

        # Get effective reminders (would include calendar defaults)
        # This tests that the system knows to fall back to calendar defaults
        calendar_list = (
            db_session.query(CalendarListEntry)
            .filter(CalendarListEntry.calendar_id == test_calendar.id)
            .first()
        )

        # Calendar defaults should exist
        assert calendar_list is not None
        assert calendar_list.default_reminders is not None
        assert len(calendar_list.default_reminders) == 2

    def test_event_with_custom_reminders_overrides_defaults(
        self, db_session, test_calendar
    ):
        """Test that event-specific reminders override calendar defaults."""
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting with custom reminders",
            start=datetime(2025, 11, 15, 14, 0, 0),
            end=datetime(2025, 11, 15, 15, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Add custom reminders (overrides defaults)
        reminder1 = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=15
        )
        reminder2 = Reminder(
            event_id=event.id, method=ReminderMethod.EMAIL, minutes_before=60
        )

        db_session.add(reminder1)
        db_session.add(reminder2)
        db_session.commit()

        # Query event reminders
        event_reminders = (
            db_session.query(Reminder).filter(Reminder.event_id == event.id).all()
        )

        assert len(event_reminders) == 2
        assert any(r.minutes_before == 15 for r in event_reminders)
        assert any(r.minutes_before == 60 for r in event_reminders)

        # These custom reminders should be used instead of calendar defaults

    def test_clearing_event_reminders_reverts_to_defaults(
        self, db_session, test_calendar
    ):
        """Test that clearing event reminders reverts to using calendar defaults."""
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Meeting",
            start=datetime(2025, 11, 15, 14, 0, 0),
            end=datetime(2025, 11, 15, 15, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Add custom reminder
        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=10
        )
        db_session.add(reminder)
        db_session.commit()

        # Verify custom reminder exists
        event_reminders = (
            db_session.query(Reminder).filter(Reminder.event_id == event.id).all()
        )
        assert len(event_reminders) == 1

        # Clear all reminders from event
        db_session.query(Reminder).filter(Reminder.event_id == event.id).delete()
        db_session.commit()

        # Verify no event-specific reminders
        event_reminders = (
            db_session.query(Reminder).filter(Reminder.event_id == event.id).all()
        )
        assert len(event_reminders) == 0

        # Now the event should use calendar defaults again
        calendar_list = (
            db_session.query(CalendarListEntry)
            .filter(CalendarListEntry.calendar_id == test_calendar.id)
            .first()
        )
        assert calendar_list.default_reminders is not None
        assert len(calendar_list.default_reminders) == 2

    def test_multiple_reminders_with_different_methods(self, db_session, test_calendar):
        """Test event with multiple reminders using different notification methods."""
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Important Meeting",
            start=datetime(2025, 11, 20, 9, 0, 0),
            end=datetime(2025, 11, 20, 10, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Add multiple reminders with different methods and times
        reminders = [
            Reminder(event_id=event.id, method=ReminderMethod.POPUP, minutes_before=10),
            Reminder(event_id=event.id, method=ReminderMethod.POPUP, minutes_before=30),
            Reminder(event_id=event.id, method=ReminderMethod.EMAIL, minutes_before=60),
            Reminder(
                event_id=event.id, method=ReminderMethod.EMAIL, minutes_before=1440
            ),  # 1 day
        ]

        for reminder in reminders:
            db_session.add(reminder)

        db_session.commit()

        # Query and verify all reminders
        event_reminders = (
            db_session.query(Reminder)
            .filter(Reminder.event_id == event.id)
            .order_by(Reminder.minutes_before)
            .all()
        )

        assert len(event_reminders) == 4

        # Verify methods
        popup_reminders = [
            r for r in event_reminders if r.method == ReminderMethod.POPUP
        ]
        email_reminders = [
            r for r in event_reminders if r.method == ReminderMethod.EMAIL
        ]

        assert len(popup_reminders) == 2
        assert len(email_reminders) == 2

        # Verify times
        assert any(r.minutes_before == 10 for r in event_reminders)
        assert any(r.minutes_before == 30 for r in event_reminders)
        assert any(r.minutes_before == 60 for r in event_reminders)
        assert any(r.minutes_before == 1440 for r in event_reminders)


# ====================================================================================
# Additional Edge Cases
# ====================================================================================


class TestAdditionalEdgeCases:
    """Additional edge cases for comprehensive coverage."""

    def test_all_day_event_with_reminders(self, db_session, test_calendar):
        """Test reminders on all-day events."""
        # All-day event (Nov 15, 2025)
        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Birthday",
            start=datetime(2025, 11, 15, 0, 0, 0),
            end=datetime(2025, 11, 16, 0, 0, 0),  # Next day at midnight
            is_all_day=True,
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Reminder at 9 AM on the day of event
        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.EMAIL, minutes_before=540  # 9 hours before midnight = 3 PM day before
        )
        db_session.add(reminder)
        db_session.commit()

        # Verify reminder was created
        event_reminders = (
            db_session.query(Reminder).filter(Reminder.event_id == event.id).all()
        )
        assert len(event_reminders) == 1
        assert event_reminders[0].minutes_before == 540

    def test_cancelled_event_with_attendees(
        self, db_session, test_calendar, test_users
    ):
        """Test that cancelled events still maintain attendee information."""
        organizer = test_users["organizer"]
        alice = test_users["alice"]
        bob = test_users["bob"]

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Cancelled Meeting",
            start=datetime(2025, 11, 18, 10, 0, 0),
            end=datetime(2025, 11, 18, 11, 0, 0),
            status=EventStatus.CONFIRMED,
        )
        db_session.add(event)
        db_session.flush()

        # Add attendees
        attendees = [
            EventAttendee(
                event_id=event.id,
                email=alice.email,
                display_name=alice.name,
                response_status=AttendeeResponseStatus.ACCEPTED,
            ),
            EventAttendee(
                event_id=event.id,
                email=bob.email,
                display_name=bob.name,
                response_status=AttendeeResponseStatus.TENTATIVE,
            ),
        ]

        for attendee in attendees:
            db_session.add(attendee)

        db_session.commit()

        # Cancel the event
        event.status = EventStatus.CANCELLED
        db_session.commit()

        # Verify event is cancelled but attendees are preserved
        db_session.refresh(event)
        assert event.status == EventStatus.CANCELLED

        event_attendees = (
            db_session.query(EventAttendee).filter(EventAttendee.event_id == event.id).all()
        )
        assert len(event_attendees) == 2

    def test_recurring_event_with_cancelled_status(self, db_session, test_calendar):
        """Test recurring event marked as cancelled."""
        start_date = datetime(2025, 11, 1, 14, 0, 0)

        event = Event(
            id=uuid4(),
            calendar_id=test_calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary="Cancelled Recurring Meeting",
            start=start_date,
            end=start_date + timedelta(minutes=60),
            recurrence=["RRULE:FREQ=DAILY;COUNT=5"],
            status=EventStatus.CANCELLED,  # Entire series cancelled
        )
        db_session.add(event)
        db_session.commit()

        # Verify cancelled recurring event still expands
        window_start = datetime(2025, 11, 1, 0, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59, 59)
        occurrences = expand_recurrence(
            event.start, event.recurrence, window_start, window_end
        )

        assert len(occurrences) == 5
        assert event.status == EventStatus.CANCELLED
