from app.db import Base

# Import all models
from app.models.models import (
    User,
    Calendar,
    CalendarListEntry,
    Event,
    EventAttendee,
    CalendarACL,
    Reminder,
    # Enums
    CalendarRole,
    ReminderMethod,
    EventStatus,
    AttendeeResponseStatus,
)

# Import legacy models
from app.models.gym_models import GymEvent

__all__ = [
    "Base",
    # New models
    "User",
    "Calendar",
    "CalendarListEntry",
    "Event",
    "EventAttendee",
    "CalendarACL",
    "Reminder",
    # Enums
    "CalendarRole",
    "ReminderMethod",
    "EventStatus",
    "AttendeeResponseStatus",
    # Legacy
    "GymEvent",
]
