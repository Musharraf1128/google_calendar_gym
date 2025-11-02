"""
Event management endpoints.

Provides endpoints for:
- Listing events with recurrence expansion
- Creating events with attendees
- Updating events
- Managing event attendees
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID

from app.db import get_db
from app.models.models import Event, Calendar, EventAttendee, User
from app.schemas import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventWithDetails,
    EventAttendeeCreate,
    EventAttendeeUpdate,
    EventAttendeeResponse,
    ReminderCreate,
    ReminderResponse,
)
from app.utils.recurrence import expand_recurrence

router = APIRouter()


@router.get("/calendars/{calendar_id}/events", response_model=List[EventResponse])
async def get_calendar_events(
    calendar_id: UUID,
    start: Optional[datetime] = Query(None, description="Start of time window"),
    end: Optional[datetime] = Query(None, description="End of time window"),
    expand_recurring: bool = Query(True, description="Expand recurring events"),
    db: Session = Depends(get_db),
):
    """
    Get events for a calendar within a time window.

    This endpoint:
    - Returns all events in the calendar
    - Optionally filters by time window (start/end)
    - Expands recurring events into individual instances if expand_recurring=True

    Args:
        calendar_id: UUID of the calendar
        start: Start of time window (optional)
        end: End of time window (optional)
        expand_recurring: Whether to expand recurring events (default: True)
        db: Database session

    Returns:
        List of events (expanded if recurring)
    """
    # Verify calendar exists
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar with id {calendar_id} not found",
        )

    # Build query
    query = db.query(Event).filter(Event.calendar_id == calendar_id)

    # Apply time window filter if provided
    if start and end:
        # For events with recurrence, we need to get all potentially relevant events
        # For non-recurring events, filter by start/end time
        query = query.filter(Event.start <= end, Event.end >= start)
    elif start:
        query = query.filter(Event.end >= start)
    elif end:
        query = query.filter(Event.start <= end)

    events = query.all()

    # If not expanding recurrence or no time window, return events as-is
    if not expand_recurring or (not start and not end):
        return events

    # Expand recurring events
    expanded_events = []

    for event in events:
        if event.recurrence:
            # Parse recurrence field (expecting list of strings)
            try:
                if isinstance(event.recurrence, dict) and "rules" in event.recurrence:
                    recurrence_rules = event.recurrence["rules"]
                elif isinstance(event.recurrence, list):
                    recurrence_rules = event.recurrence
                else:
                    # Not a proper recurrence format, treat as single event
                    expanded_events.append(event)
                    continue

                # Expand recurrence within time window
                # Use datetime.min/max with UTC timezone
                min_dt = datetime.min.replace(tzinfo=timezone.utc)
                max_dt = datetime.max.replace(tzinfo=timezone.utc)
                occurrences = expand_recurrence(
                    event_start=event.start,
                    recurrence_field=recurrence_rules,
                    window_start=start or min_dt,
                    window_end=end or max_dt,
                )

                # Create event instances for each occurrence
                # Note: These are virtual instances, not stored in DB
                for occurrence in occurrences:
                    # Calculate duration
                    duration = event.end - event.start

                    # Create event instance
                    event_instance = EventResponse(
                        id=event.id,
                        calendar_id=event.calendar_id,
                        summary=event.summary,
                        description=event.description,
                        start=occurrence,
                        end=occurrence + duration,
                        recurrence=event.recurrence,
                        iCalUID=event.iCalUID,
                        status=event.status,
                        is_all_day=event.is_all_day,
                        location=event.location,
                        created_at=event.created_at,
                        updated_at=event.updated_at,
                    )
                    expanded_events.append(event_instance)

            except Exception as e:
                # If expansion fails, return the original event
                print(f"Error expanding recurrence for event {event.id}: {str(e)}")
                expanded_events.append(event)
        else:
            # Non-recurring event
            expanded_events.append(event)

    return expanded_events


@router.get("/events/{event_id}", response_model=EventWithDetails)
async def get_event(event_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific event with attendees and reminders.

    Args:
        event_id: UUID of the event
        db: Database session

    Returns:
        Event with details (attendees, reminders)
    """
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .options(joinedload(Event.attendees), joinedload(Event.reminders))
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    return event


@router.post(
    "/calendars/{calendar_id}/events",
    response_model=EventWithDetails,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    calendar_id: UUID, event_data: EventCreate, db: Session = Depends(get_db)
):
    """
    Create a new event in a calendar.

    This endpoint supports:
    - Basic event creation
    - Recurrence rules

    Note: To add attendees or reminders, use the separate endpoints after creating the event.

    Args:
        calendar_id: UUID of the calendar
        event_data: Event creation data
        db: Database session

    Returns:
        Created event
    """
    # Verify calendar exists
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar with id {calendar_id} not found",
        )

    # Ensure calendar_id matches
    if event_data.calendar_id != calendar_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calendar ID in request body does not match URL parameter",
        )

    # Validate event times
    if event_data.end <= event_data.start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event end time must be after start time",
        )

    # Create event
    new_event = Event(
        calendar_id=calendar_id,
        summary=event_data.summary,
        description=event_data.description,
        start=event_data.start,
        end=event_data.end,
        recurrence=event_data.recurrence,
        iCalUID=event_data.iCalUID,
        status=event_data.status,
        is_all_day=event_data.is_all_day,
        location=event_data.location,
    )
    db.add(new_event)
    db.commit()

    # Reload with relationships
    db.refresh(new_event)
    event_with_details = (
        db.query(Event)
        .filter(Event.id == new_event.id)
        .options(joinedload(Event.attendees), joinedload(Event.reminders))
        .first()
    )

    return event_with_details


@router.patch("/events/{event_id}", response_model=EventWithDetails)
async def update_event(
    event_id: UUID, event_update: EventUpdate, db: Session = Depends(get_db)
):
    """
    Update an event and propagate updates.

    This endpoint:
    - Updates event fields
    - Maintains attendee and reminder relationships
    - Can update recurrence rules

    Note: For recurring events, this updates the master event.
    Individual instances are not stored separately.

    Args:
        event_id: UUID of the event to update
        event_update: Fields to update
        db: Database session

    Returns:
        Updated event with details
    """
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .options(joinedload(Event.attendees), joinedload(Event.reminders))
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    # Update fields if provided
    update_data = event_update.model_dump(exclude_unset=True)

    # DIAGNOSTIC LOGGING
    if "start" in update_data or "end" in update_data:
        print("\n" + "=" * 80)
        print("📥 BACKEND: Event Update Received")
        print("=" * 80)
        print(f"Event ID: {event_id}")
        print(f"Event Summary: {event.summary}")
        print("\nCURRENT VALUES (in DB):")
        print(f"  Start: {event.start}")
        print(f"  Start ISO: {event.start.isoformat()}")
        print(f"  End: {event.end}")
        print(f"  End ISO: {event.end.isoformat()}")
        print("\nUPDATE REQUEST:")
        if "start" in update_data:
            print(f"  New Start: {update_data['start']}")
            print(f"  New Start ISO: {update_data['start'].isoformat()}")
        if "end" in update_data:
            print(f"  New End: {update_data['end']}")
            print(f"  New End ISO: {update_data['end'].isoformat()}")
        print("=" * 80 + "\n")

    # Validate times if both are being updated
    if "start" in update_data and "end" in update_data:
        if update_data["end"] <= update_data["start"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time must be after start time",
            )
    elif "start" in update_data:
        if event.end <= update_data["start"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time must be after new start time",
            )
    elif "end" in update_data:
        if update_data["end"] <= event.start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New end time must be after event start time",
            )

    # Apply updates
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    # DIAGNOSTIC LOGGING
    if "start" in update_data or "end" in update_data:
        print("=" * 80)
        print("💾 BACKEND: Event Updated in DB")
        print("=" * 80)
        print("STORED VALUES (UTC in DB):")
        print(f"  Start: {event.start}")
        print(f"  Start ISO: {event.start.isoformat()}")
        print(f"  End: {event.end}")
        print(f"  End ISO: {event.end.isoformat()}")
        print("=" * 80 + "\n")

    return event


@router.post(
    "/events/{event_id}/invite",
    response_model=EventAttendeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_event_attendee(
    event_id: UUID, attendee_data: EventAttendeeCreate, db: Session = Depends(get_db)
):
    """
    Add an attendee to an event (send invitation).

    Args:
        event_id: UUID of the event
        attendee_data: Attendee information
        db: Database session

    Returns:
        Created attendee entry
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    # Ensure event_id matches
    if attendee_data.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event ID in request body does not match URL parameter",
        )

    # Check if attendee already exists
    existing_attendee = (
        db.query(EventAttendee)
        .filter(
            EventAttendee.event_id == event_id,
            EventAttendee.email == attendee_data.email,
        )
        .first()
    )

    if existing_attendee:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendee {attendee_data.email} is already invited to this event",
        )

    # Check if user exists in our system
    user = None
    if attendee_data.email:
        user = db.query(User).filter(User.email == attendee_data.email).first()

    # Create attendee
    new_attendee = EventAttendee(
        event_id=event_id,
        user_id=user.id if user else attendee_data.user_id,
        email=attendee_data.email,
        display_name=attendee_data.display_name,
        response_status=attendee_data.response_status,
        is_organizer=attendee_data.is_organizer,
        is_optional=attendee_data.is_optional,
    )
    db.add(new_attendee)
    db.commit()
    db.refresh(new_attendee)

    return new_attendee


@router.get("/events/{event_id}/attendees", response_model=List[EventAttendeeResponse])
async def get_event_attendees(event_id: UUID, db: Session = Depends(get_db)):
    """
    Get all attendees for an event.

    Args:
        event_id: UUID of the event
        db: Database session

    Returns:
        List of attendees
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    attendees = db.query(EventAttendee).filter(EventAttendee.event_id == event_id).all()

    return attendees


@router.patch(
    "/events/{event_id}/respond",
    response_model=EventAttendeeResponse,
)
async def respond_to_event(
    event_id: UUID,
    attendee_update: EventAttendeeUpdate,
    user_email: str = Query(..., description="Email of the attendee responding"),
    db: Session = Depends(get_db),
):
    """
    Update an attendee's response status for an event.

    This endpoint allows attendees to accept, decline, or tentatively accept
    an event invitation.

    Args:
        event_id: UUID of the event
        attendee_update: Updated attendee information (response_status)
        user_email: Email of the attendee responding
        db: Database session

    Returns:
        Updated attendee entry
    """
    # Verify event exists
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .options(joinedload(Event.attendees))
        .first()
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    # Find the attendee
    attendee = (
        db.query(EventAttendee)
        .filter(
            EventAttendee.event_id == event_id,
            EventAttendee.email == user_email,
        )
        .first()
    )

    if not attendee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendee {user_email} not found for this event",
        )

    # Store old status for notification
    old_status = attendee.response_status

    # Update response status
    update_data = attendee_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attendee, field, value)

    db.commit()
    db.refresh(attendee)

    # Log notification if status changed
    if "response_status" in update_data and old_status != attendee.response_status:
        from app.models.models import NotificationLog, ReminderMethod

        # Create notification for organizer
        if event.organizer_id:
            notification = NotificationLog(
                event_id=event_id,
                user_id=event.organizer_id,
                reminder_method=ReminderMethod.EMAIL,
                minutes_before=0,
                scheduled_time=datetime.now(timezone.utc),
                event_summary=event.summary,
                event_start=event.start,
                message=f"{attendee.display_name or attendee.email} has {attendee.response_status.value} the invitation to '{event.summary}'",
            )
            db.add(notification)
            db.commit()

            print(
                f"📧 Notification: {attendee.email} {attendee.response_status.value} event '{event.summary}'"
            )

    return attendee


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: UUID, db: Session = Depends(get_db)):
    """
    Delete an event.

    This will cascade delete:
    - All attendees
    - All reminders

    Args:
        event_id: UUID of the event to delete
        db: Database session
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    db.delete(event)
    db.commit()

    return None


@router.post("/events/{event_id}/reminders", response_model=List[ReminderResponse])
async def set_event_reminders(
    event_id: UUID, reminders: List[ReminderCreate], db: Session = Depends(get_db)
):
    """
    Set custom reminders for an event (overrides defaults).

    This endpoint allows you to override the default reminders from CalendarListEntry
    with event-specific reminders.

    Args:
        event_id: UUID of the event
        reminders: List of reminders to set
        db: Database session

    Returns:
        List of created reminders

    Example request body:
        [
            {"method": "popup", "minutes_before": 30},
            {"method": "email", "minutes_before": 60}
        ]
    """
    from app.services.reminder_service import (
        set_event_reminders as set_reminders_service,
    )

    try:
        # Convert Pydantic models to dicts
        reminder_dicts = [r.dict() for r in reminders]

        # Set the reminders using the service
        event = set_reminders_service(db, event_id, reminder_dicts)

        # Return the updated reminders
        return [
            ReminderResponse(
                id=r.id,
                event_id=r.event_id,
                method=r.method,
                minutes_before=r.minutes_before,
            )
            for r in event.reminders
        ]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/events/{event_id}/reminders", response_model=List[ReminderResponse])
async def get_event_reminders(event_id: UUID, db: Session = Depends(get_db)):
    """
    Get all reminders for an event.

    Args:
        event_id: UUID of the event
        db: Database session

    Returns:
        List of reminders
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

    return [
        ReminderResponse(
            id=r.id,
            event_id=r.event_id,
            method=r.method,
            minutes_before=r.minutes_before,
        )
        for r in event.reminders
    ]
