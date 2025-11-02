"""
Event Service for managing calendar events with attendee propagation.

This service implements Google Calendar-like event propagation:
- When an organizer creates an event with attendees, copies are created in each attendee's calendar
- All copies are linked via iCalUID
- When the organizer updates an event, changes propagate to all attendee copies
- When an attendee responds, their response is reflected in the organizer's event
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from uuid import UUID, uuid4

from app.models.models import (
    Event,
    EventAttendee,
    User,
    Calendar,
    CalendarListEntry,
    AttendeeResponseStatus,
    EventStatus,
)


def generate_ical_uid() -> str:
    """
    Generate a unique iCalUID for linking organizer and attendee event copies.

    Returns:
        A unique iCalUID string
    """
    return f"{uuid4()}@calendar.app"


def get_or_create_user_calendar(db: Session, user_id: UUID) -> Calendar:
    """
    Get or create a primary calendar for a user.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        The user's primary calendar
    """
    # Check if user has a primary calendar
    entry = (
        db.query(CalendarListEntry)
        .filter(
            CalendarListEntry.user_id == user_id, CalendarListEntry.is_primary.is_(True)
        )
        .first()
    )

    if entry:
        return entry.calendar

    # If no primary calendar, create one
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    calendar = Calendar(
        id=uuid4(),
        title=f"{user.name or user.email}'s Calendar",
        timezone="UTC",
        owner_id=user_id,
        description="Primary calendar",
    )
    db.add(calendar)

    # Create calendar list entry
    list_entry = CalendarListEntry(
        user_id=user_id, calendar_id=calendar.id, is_primary=True
    )
    db.add(list_entry)
    db.commit()
    db.refresh(calendar)

    return calendar


def create_event(
    db: Session, calendar_id: UUID, organizer_email: str, payload: Dict[str, Any]
) -> Event:
    """
    Create an event and propagate copies to attendees.

    When an event is created with attendees, this function:
    1. Creates the organizer's event with a unique iCalUID
    2. Creates a copy of the event in each attendee's calendar with the same iCalUID
    3. Each copy includes the full attendee list

    Args:
        db: Database session
        calendar_id: ID of the organizer's calendar
        organizer_email: Email of the event organizer
        payload: Event data including:
            - summary (required)
            - start (required, datetime)
            - end (required, datetime)
            - description (optional)
            - location (optional)
            - attendees (optional): List of dicts with 'email', 'display_name', 'is_optional'
            - status (optional)
            - is_all_day (optional)

    Returns:
        The created organizer event

    Example:
        >>> payload = {
        ...     "summary": "Team Meeting",
        ...     "start": datetime(2025, 1, 15, 10, 0),
        ...     "end": datetime(2025, 1, 15, 11, 0),
        ...     "attendees": [
        ...         {"email": "alice@example.com", "display_name": "Alice"},
        ...         {"email": "bob@example.com", "display_name": "Bob"}
        ...     ]
        ... }
        >>> event = create_event(db, cal_id, "organizer@example.com", payload)
    """
    # Generate unique iCalUID for this event
    ical_uid = generate_ical_uid()

    # Extract attendees from payload
    attendees_data = payload.pop("attendees", [])

    # Create the organizer's event
    organizer_event = Event(
        id=uuid4(),
        calendar_id=calendar_id,
        iCalUID=ical_uid,
        summary=payload.get("summary"),
        description=payload.get("description"),
        start=payload.get("start"),
        end=payload.get("end"),
        location=payload.get("location"),
        status=payload.get("status", EventStatus.CONFIRMED),
        is_all_day=payload.get("is_all_day", False),
        recurrence=payload.get("recurrence"),
    )
    db.add(organizer_event)
    db.flush()  # Get the event ID

    # Create attendee records for the organizer's event
    all_attendees = []

    # Add organizer as an attendee
    organizer_attendee = EventAttendee(
        event_id=organizer_event.id,
        email=organizer_email,
        display_name=organizer_email.split("@")[0],
        response_status=AttendeeResponseStatus.ACCEPTED,
        is_organizer=True,
        is_optional=False,
    )
    db.add(organizer_attendee)
    all_attendees.append(
        {
            "email": organizer_email,
            "display_name": organizer_email.split("@")[0],
            "is_organizer": True,
            "is_optional": False,
            "response_status": AttendeeResponseStatus.ACCEPTED,
        }
    )

    # Add other attendees
    for attendee_data in attendees_data:
        attendee = EventAttendee(
            event_id=organizer_event.id,
            email=attendee_data["email"],
            display_name=attendee_data.get(
                "display_name", attendee_data["email"].split("@")[0]
            ),
            response_status=AttendeeResponseStatus.NEEDS_ACTION,
            is_organizer=False,
            is_optional=attendee_data.get("is_optional", False),
        )
        db.add(attendee)
        all_attendees.append(
            {
                "email": attendee_data["email"],
                "display_name": attendee_data.get(
                    "display_name", attendee_data["email"].split("@")[0]
                ),
                "is_organizer": False,
                "is_optional": attendee_data.get("is_optional", False),
                "response_status": AttendeeResponseStatus.NEEDS_ACTION,
            }
        )

    # Create copies for each non-organizer attendee
    for attendee_data in attendees_data:
        # Find the attendee user
        attendee_user = (
            db.query(User).filter(User.email == attendee_data["email"]).first()
        )

        if attendee_user:
            # Get or create attendee's calendar
            attendee_calendar = get_or_create_user_calendar(db, attendee_user.id)

            # Create event copy in attendee's calendar
            attendee_event = Event(
                id=uuid4(),
                calendar_id=attendee_calendar.id,
                iCalUID=ical_uid,  # Same iCalUID links all copies
                summary=organizer_event.summary,
                description=organizer_event.description,
                start=organizer_event.start,
                end=organizer_event.end,
                location=organizer_event.location,
                status=organizer_event.status,
                is_all_day=organizer_event.is_all_day,
                recurrence=organizer_event.recurrence,
            )
            db.add(attendee_event)
            db.flush()

            # Create attendee records for this copy (all attendees included)
            for att in all_attendees:
                event_attendee = EventAttendee(
                    event_id=attendee_event.id,
                    email=att["email"],
                    display_name=att["display_name"],
                    response_status=att["response_status"],
                    is_organizer=att["is_organizer"],
                    is_optional=att["is_optional"],
                )
                db.add(event_attendee)

    db.commit()
    db.refresh(organizer_event)

    return organizer_event


def update_event(db: Session, event_id: UUID, updates: Dict[str, Any]) -> Event:
    """
    Update an event and propagate changes to all attendee copies.

    When an organizer updates an event, this function:
    1. Updates the organizer's event
    2. Finds all events with the same iCalUID (attendee copies)
    3. Propagates the updates to all copies

    Args:
        db: Database session
        event_id: ID of the organizer's event to update
        updates: Dictionary of fields to update (summary, start, end, location, etc.)

    Returns:
        The updated organizer event

    Note:
        Attendee list updates are not supported in this version.
        Status changes propagate to all copies.
    """
    # Get the organizer's event
    organizer_event = db.query(Event).filter(Event.id == event_id).first()

    if not organizer_event:
        raise ValueError(f"Event with id {event_id} not found")

    ical_uid = organizer_event.iCalUID

    if not ical_uid:
        raise ValueError(f"Event {event_id} has no iCalUID and cannot be propagated")

    # Update the organizer's event
    for key, value in updates.items():
        if hasattr(organizer_event, key) and key not in [
            "id",
            "calendar_id",
            "iCalUID",
            "created_at",
        ]:
            setattr(organizer_event, key, value)

    # Find all attendee copies (events with same iCalUID but different calendar)
    attendee_events = (
        db.query(Event).filter(Event.iCalUID == ical_uid, Event.id != event_id).all()
    )

    # Propagate updates to all attendee copies
    for attendee_event in attendee_events:
        for key, value in updates.items():
            if hasattr(attendee_event, key) and key not in [
                "id",
                "calendar_id",
                "iCalUID",
                "created_at",
            ]:
                setattr(attendee_event, key, value)

    db.commit()
    db.refresh(organizer_event)

    return organizer_event


def update_attendee_response(
    db: Session,
    event_id: UUID,
    attendee_email: str,
    response_status: AttendeeResponseStatus,
) -> EventAttendee:
    """
    Update an attendee's response status and propagate to the organizer's event.

    When an attendee responds to an event invitation, this function:
    1. Updates the attendee's response on their event copy
    2. Finds the organizer's event (same iCalUID)
    3. Updates the attendee's response on the organizer's event

    Args:
        db: Database session
        event_id: ID of the attendee's event copy
        attendee_email: Email of the attendee responding
        response_status: New response status (ACCEPTED, DECLINED, TENTATIVE, etc.)

    Returns:
        The updated EventAttendee record from the attendee's event

    Example:
        >>> update_attendee_response(
        ...     db, attendee_event_id,
        ...     "alice@example.com",
        ...     AttendeeResponseStatus.ACCEPTED
        ... )
    """
    # Get the attendee's event copy
    attendee_event = db.query(Event).filter(Event.id == event_id).first()

    if not attendee_event:
        raise ValueError(f"Event with id {event_id} not found")

    ical_uid = attendee_event.iCalUID

    if not ical_uid:
        raise ValueError(f"Event {event_id} has no iCalUID and cannot be propagated")

    # Update attendee response on their event copy
    attendee_record = (
        db.query(EventAttendee)
        .filter(
            EventAttendee.event_id == event_id, EventAttendee.email == attendee_email
        )
        .first()
    )

    if not attendee_record:
        raise ValueError(f"Attendee {attendee_email} not found on event {event_id}")

    attendee_record.response_status = response_status

    # Find all other events with same iCalUID (including organizer's)
    all_event_copies = (
        db.query(Event).filter(Event.iCalUID == ical_uid, Event.id != event_id).all()
    )

    # Update the attendee's response on all other copies
    for event_copy in all_event_copies:
        attendee_on_copy = (
            db.query(EventAttendee)
            .filter(
                EventAttendee.event_id == event_copy.id,
                EventAttendee.email == attendee_email,
            )
            .first()
        )

        if attendee_on_copy:
            attendee_on_copy.response_status = response_status

    db.commit()
    db.refresh(attendee_record)

    return attendee_record


def get_event_by_ical_uid(
    db: Session, ical_uid: str, calendar_id: Optional[UUID] = None
) -> Optional[Event]:
    """
    Get an event by its iCalUID, optionally filtered by calendar.

    Args:
        db: Database session
        ical_uid: The iCalUID to search for
        calendar_id: Optional calendar ID to filter by

    Returns:
        The event if found, None otherwise
    """
    query = db.query(Event).filter(Event.iCalUID == ical_uid)

    if calendar_id:
        query = query.filter(Event.calendar_id == calendar_id)

    return query.first()


def get_all_event_copies(db: Session, ical_uid: str) -> List[Event]:
    """
    Get all event copies (organizer + attendees) linked by iCalUID.

    Args:
        db: Database session
        ical_uid: The iCalUID linking the events

    Returns:
        List of all event copies
    """
    return db.query(Event).filter(Event.iCalUID == ical_uid).all()
