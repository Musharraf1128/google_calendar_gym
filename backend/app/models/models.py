from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Enum,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.db import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# Enums
class CalendarRole(str, enum.Enum):
    OWNER = "owner"
    WRITER = "writer"
    READER = "reader"
    FREE_BUSY_READER = "freeBusyReader"


class ReminderMethod(str, enum.Enum):
    POPUP = "popup"
    EMAIL = "email"


class EventStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    NEEDS_ACTION = "needsAction"
    COMPLETED = "completed"


class EventTransparency(str, enum.Enum):
    """Event transparency for free/busy time."""

    opaque = "opaque"  # Default - blocks time in free/busy
    transparent = "transparent"  # Doesn't block time in free/busy


class EventVisibility(str, enum.Enum):
    """Event visibility/privacy level."""

    default = "default"  # Default visibility (inherits from calendar)
    public = "public"  # Public event
    private = "private"  # Private event
    confidential = "confidential"  # Confidential event


class AttendeeResponseStatus(str, enum.Enum):
    NEEDS_ACTION = "needsAction"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    ACCEPTED = "accepted"


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    owned_calendars = relationship(
        "Calendar", back_populates="owner", foreign_keys="Calendar.owner_id"
    )
    calendar_entries = relationship(
        "CalendarListEntry", back_populates="user", cascade="all, delete-orphan"
    )
    event_attendances = relationship("EventAttendee", back_populates="user")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    timezone = Column(String(100), nullable=False, default="UTC")
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    owner = relationship(
        "User", back_populates="owned_calendars", foreign_keys=[owner_id]
    )
    events = relationship(
        "Event", back_populates="calendar", cascade="all, delete-orphan"
    )
    calendar_entries = relationship(
        "CalendarListEntry", back_populates="calendar", cascade="all, delete-orphan"
    )
    acl_entries = relationship(
        "CalendarACL", back_populates="calendar", cascade="all, delete-orphan"
    )


class CalendarListEntry(Base):
    __tablename__ = "calendar_list_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    calendar_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    access_role = Column(
        Enum(CalendarRole),
        nullable=False,
        default=CalendarRole.READER,
        index=True,
    )
    color = Column(String(50), nullable=True)
    default_reminders = Column(JSON, nullable=True)  # Store array of {method, minutes}
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="calendar_entries")
    calendar = relationship("Calendar", back_populates="calendar_entries")

    # Unique constraint: a user can only have one entry per calendar
    __table_args__ = (
        Index("idx_user_calendar", "user_id", "calendar_id", unique=True),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    calendar_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Start/End times - support both date (all-day) and dateTime (timed) forms
    start = Column(DateTime, nullable=False, index=True)
    end = Column(DateTime, nullable=False, index=True)
    is_all_day = Column(Boolean, default=False, nullable=False)

    # Google Calendar fields
    location = Column(String(500), nullable=True)
    status = Column(Enum(EventStatus), default=EventStatus.CONFIRMED, nullable=False)
    transparency = Column(
        Enum(EventTransparency), default=EventTransparency.opaque, nullable=False
    )  # opaque (blocks time) or transparent (doesn't block)
    visibility = Column(
        Enum(EventVisibility), default=EventVisibility.default, nullable=False
    )  # default, public, private, confidential
    color_id = Column(
        Integer, default=0, nullable=True
    )  # Event color (0-11 per Google)

    # Creator and Organizer
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # User who created the event
    organizer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # User who organizes the event (can be different from creator)

    # Recurrence
    recurrence = Column(JSON, nullable=True)  # Store recurrence rules as JSON or text
    iCalUID = Column(
        String(255), nullable=True, index=True
    )  # Not unique - multiple event copies share same iCalUID

    # Metadata
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    calendar = relationship("Calendar", back_populates="events")
    creator = relationship("User", foreign_keys=[creator_id], backref="created_events")
    organizer = relationship(
        "User", foreign_keys=[organizer_id], backref="organized_events"
    )
    attendees = relationship(
        "EventAttendee", back_populates="event", cascade="all, delete-orphan"
    )
    reminders = relationship(
        "Reminder", back_populates="event", cascade="all, delete-orphan"
    )
    linked_tasks = relationship("Task", back_populates="related_event")

    # Indexes
    __table_args__ = (
        Index("idx_event_start_end", "start", "end"),
        Index("idx_event_calendar_start", "calendar_id", "start"),
        Index("idx_event_creator", "creator_id"),
        Index("idx_event_organizer", "organizer_id"),
        Index(
            "idx_calendar_icaluid", "calendar_id", "iCalUID", unique=True
        ),  # Each calendar can have only one event per iCalUID
    )


class EventAttendee(Base):
    __tablename__ = "event_attendees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    response_status = Column(
        Enum(AttendeeResponseStatus),
        default=AttendeeResponseStatus.NEEDS_ACTION,
        nullable=False,
    )
    is_organizer = Column(Boolean, default=False)
    is_optional = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="attendees")
    user = relationship("User", back_populates="event_attendances")

    # Index
    __table_args__ = (Index("idx_attendee_event_email", "event_id", "email"),)


class CalendarACL(Base):
    __tablename__ = "calendar_acl"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    grantee = Column(String(255), nullable=False)  # Email or domain
    role = Column(Enum(CalendarRole), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    calendar = relationship("Calendar", back_populates="acl_entries")

    # Unique constraint: one role per grantee per calendar
    __table_args__ = (
        Index("idx_calendar_grantee", "calendar_id", "grantee", unique=True),
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    method = Column(Enum(ReminderMethod), nullable=False)
    minutes_before = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="reminders")

    # Index
    __table_args__ = (Index("idx_reminder_event", "event_id"),)


class NotificationLog(Base):
    """
    Log of reminder notifications that have been sent.
    This table simulates notification delivery for testing/auditing purposes.
    """

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reminder_method = Column(Enum(ReminderMethod), nullable=False)
    minutes_before = Column(Integer, nullable=False)
    scheduled_time = Column(
        DateTime, nullable=False
    )  # When the reminder was scheduled to fire
    sent_time = Column(
        DateTime, default=utc_now, nullable=False
    )  # When the notification was actually sent
    event_summary = Column(String(500), nullable=True)  # Cached event summary
    event_start = Column(DateTime, nullable=True)  # Cached event start time
    message = Column(Text, nullable=True)  # The notification message
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Index for querying logs by event or user
    __table_args__ = (
        Index("idx_notification_event", "event_id"),
        Index("idx_notification_user", "user_id"),
        Index("idx_notification_sent_time", "sent_time"),
    )


class Task(Base):
    """
    Google Calendar-style Tasks.

    Tasks can be:
    - Standalone (just a to-do item with due date)
    - Linked to an event (related_event_id set)

    Fields match Google Calendar Tasks API:
    - title: Task title
    - notes: Task description/notes
    - due: Due date/time (optional)
    - status: needsAction or completed
    - related_event_id: Link to calendar event (optional)
    """

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    notes = Column(Text, nullable=True)
    due = Column(DateTime, nullable=True, index=True)  # Due date/time (optional)
    status = Column(
        Enum(TaskStatus), nullable=False, default=TaskStatus.NEEDS_ACTION, index=True
    )

    # Optional link to a calendar event
    related_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    completed_at = Column(DateTime, nullable=True)  # When task was marked complete
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="tasks")
    related_event = relationship("Event", back_populates="linked_tasks")

    # Indexes
    __table_args__ = (
        Index("idx_task_user_status", "user_id", "status"),
        Index("idx_task_due", "due"),
        Index("idx_task_event", "related_event_id"),
    )
