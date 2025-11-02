from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_serializer
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum


# Enums matching SQLAlchemy models
class CalendarRoleEnum(str, Enum):
    OWNER = "owner"
    WRITER = "writer"
    READER = "reader"
    FREE_BUSY_READER = "freeBusyReader"


class ReminderMethodEnum(str, Enum):
    POPUP = "popup"
    EMAIL = "email"


class EventStatusEnum(str, Enum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class TaskStatusEnum(str, Enum):
    NEEDS_ACTION = "needsAction"
    COMPLETED = "completed"


class EventTransparencyEnum(str, Enum):
    """Event transparency for free/busy time."""
    opaque = "opaque"
    transparent = "transparent"


class EventVisibilityEnum(str, Enum):
    """Event visibility/privacy level."""
    default = "default"
    public = "public"
    private = "private"
    confidential = "confidential"


class AttendeeResponseStatusEnum(str, Enum):
    NEEDS_ACTION = "needsAction"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    ACCEPTED = "accepted"


# ============ User Schemas ============
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============ Calendar Schemas ============
class CalendarBase(BaseModel):
    title: str
    timezone: str = "UTC"
    description: Optional[str] = None


class CalendarCreate(CalendarBase):
    owner_id: UUID


class CalendarUpdate(BaseModel):
    title: Optional[str] = None
    timezone: Optional[str] = None
    description: Optional[str] = None


class CalendarResponse(CalendarBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


class CalendarWithOwner(CalendarResponse):
    owner: UserResponse


# ============ CalendarListEntry Schemas ============
class CalendarListEntryBase(BaseModel):
    access_role: CalendarRoleEnum = CalendarRoleEnum.READER
    color: Optional[str] = None
    default_reminders: Optional[List[Dict[str, Any]]] = None
    is_primary: bool = False


class CalendarListEntryCreate(CalendarListEntryBase):
    user_id: UUID
    calendar_id: UUID


class CalendarListEntryUpdate(BaseModel):
    color: Optional[str] = None
    default_reminders: Optional[List[Dict[str, Any]]] = None
    is_primary: Optional[bool] = None


class CalendarListEntryResponse(CalendarListEntryBase):
    id: int
    user_id: UUID
    calendar_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


class CalendarListEntryWithDetails(CalendarListEntryResponse):
    calendar: CalendarResponse


# ============ Event Schemas ============
class EventBase(BaseModel):
    summary: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    is_all_day: bool = False
    location: Optional[str] = None
    status: EventStatusEnum = EventStatusEnum.CONFIRMED
    transparency: EventTransparencyEnum = EventTransparencyEnum.opaque
    visibility: EventVisibilityEnum = EventVisibilityEnum.default
    color_id: Optional[int] = 0
    recurrence: Optional[Any] = None  # Can be list of strings or dict with rules
    iCalUID: Optional[str] = None


class EventCreate(EventBase):
    calendar_id: UUID
    creator_id: Optional[UUID] = None
    organizer_id: Optional[UUID] = None


class EventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    location: Optional[str] = None
    status: Optional[EventStatusEnum] = None
    transparency: Optional[EventTransparencyEnum] = None
    visibility: Optional[EventVisibilityEnum] = None
    color_id: Optional[int] = None
    recurrence: Optional[Any] = None  # Can be list of strings or dict with rules
    creator_id: Optional[UUID] = None
    organizer_id: Optional[UUID] = None


class EventResponse(EventBase):
    id: UUID
    calendar_id: UUID
    creator_id: Optional[UUID] = None
    organizer_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('start', 'end', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        # If datetime is naive (no timezone), assume it's UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC and format as ISO string with 'Z' suffix
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============ EventAttendee Schemas ============
class EventAttendeeBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    response_status: AttendeeResponseStatusEnum = (
        AttendeeResponseStatusEnum.NEEDS_ACTION
    )
    is_organizer: bool = False
    is_optional: bool = False


class EventAttendeeCreate(EventAttendeeBase):
    event_id: UUID
    user_id: Optional[UUID] = None


class EventAttendeeUpdate(BaseModel):
    response_status: Optional[AttendeeResponseStatusEnum] = None
    display_name: Optional[str] = None
    is_optional: Optional[bool] = None


class EventAttendeeResponse(EventAttendeeBase):
    id: int
    event_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============ CalendarACL Schemas ============
class CalendarACLBase(BaseModel):
    grantee: str  # Email or domain
    role: CalendarRoleEnum


class CalendarACLCreate(CalendarACLBase):
    calendar_id: UUID


class CalendarACLUpdate(BaseModel):
    role: CalendarRoleEnum


class CalendarACLResponse(CalendarACLBase):
    id: int
    calendar_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============ Reminder Schemas ============
class ReminderBase(BaseModel):
    method: ReminderMethodEnum
    minutes_before: int = Field(
        ..., ge=0, description="Minutes before event to trigger reminder"
    )


class ReminderCreate(ReminderBase):
    event_id: UUID


class ReminderUpdate(BaseModel):
    method: Optional[ReminderMethodEnum] = None
    minutes_before: Optional[int] = Field(None, ge=0)


class ReminderResponse(ReminderBase):
    id: int
    event_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============ Extended Response Schemas with Relations ============
class EventWithDetails(EventResponse):
    attendees: List[EventAttendeeResponse] = []
    reminders: List[ReminderResponse] = []


class EventWithCalendar(EventWithDetails):
    calendar: CalendarResponse


class CalendarWithEvents(CalendarResponse):
    events: List[EventResponse] = []


# ============ Legacy Schemas (for backward compatibility) ============
# Keep old GymEvent schemas if needed
class GymEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime


class GymEventCreate(GymEventBase):
    user_id: int


class GymEventResponse(GymEventBase):
    id: int
    user_id: int
    google_event_id: Optional[str] = None
    is_synced: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('start_time', 'end_time', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============ Task Schemas ============
class TaskBase(BaseModel):
    title: str
    notes: Optional[str] = None
    due: Optional[datetime] = None
    status: TaskStatusEnum = TaskStatusEnum.NEEDS_ACTION
    related_event_id: Optional[UUID] = None


class TaskCreate(TaskBase):
    user_id: UUID


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    due: Optional[datetime] = None
    status: Optional[TaskStatusEnum] = None
    related_event_id: Optional[UUID] = None


class TaskResponse(TaskBase):
    id: UUID
    user_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('due', 'completed_at', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Ensure all datetime fields are serialized as UTC ISO strings with 'Z' suffix."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
