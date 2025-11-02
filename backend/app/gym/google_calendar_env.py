"""
Google Calendar Gym Environment.

A reinforcement learning environment for simulating and training agents on
Google Calendar interactions including:
- Event creation and management
- User invitations and responses
- Calendar sharing (ACLs)
- Attendee management
"""

import random
import os
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle
from io import BytesIO
import base64

# Load environment variables
load_dotenv()

from app.db import Base
from app.models.models import (
    User,
    Calendar,
    Event,
    EventAttendee,
    CalendarACL,
    CalendarListEntry,
    AttendeeResponseStatus,
    CalendarRole,
)
from app.services.event_service import (
    create_event,
    update_event,
    update_attendee_response,
)


# Google Calendar Color Palette
GOOGLE_CALENDAR_COLORS = {
    "Lavender": "#7986cb",
    "Sage": "#33b679",
    "Grape": "#8e24aa",
    "Flamingo": "#e67c73",
    "Banana": "#f6c026",
    "Tangerine": "#f5511d",
    "Peacock": "#039be5",
    "Graphite": "#616161",
    "Blueberry": "#3f51b5",
    "Basil": "#0b8043",
    "Tomato": "#d60000",
}

POPUP_TYPES = [
    "reminder_toast",
    "event_edit_modal",
    "permission_error",
    "event_created_toast",
    "sync_notification",
    "calendar_shared_toast",
    "invitation_popup",
]


class GoogleCalendarEnv:
    """
    Google Calendar Gym Environment for reinforcement learning.

    This environment simulates a Google Calendar system where agents can:
    - Create events and invite users
    - Accept/decline invitations
    - Share calendars with specific permissions
    - Update events (propagates to attendees)

    Observation Space (dict):
        - users: List of user data
        - calendars: List of calendar data
        - events: List of event data
        - acls: List of ACL entries
        - attendees: List of event attendees
        - step: Current step number

    Action Space (dict):
        - type: Action type (create_event, update_event, delete_event, accept, decline, share_calendar, invite_user)
        - params: Action-specific parameters

    Reward Function (Binary):
        - Valid action (create, update, delete, accept, decline, share): +1.0
        - Invalid action (errors, conflicts, not found): 0.0
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Google Calendar Gym environment.

        Args:
            db_path: Optional database path. If None, uses in-memory SQLite.
        """
        # Create database engine
        if db_path:
            self.engine = create_engine(
                f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
            )
        else:
            self.engine = create_engine(
                "sqlite:///:memory:", connect_args={"check_same_thread": False}
            )

        Base.metadata.create_all(bind=self.engine)

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.db: Optional[Session] = None

        # Environment state
        self.step_count = 0
        self.max_steps = 100
        self.episode_reward = 0.0

        # UI Realism configuration
        self.ui_realism = os.getenv("UI_REALISM", "false").lower() == "true"
        self.popup_history: List[str] = []
        self.color_assignments: Dict[str, str] = {}

        # Observation and action space descriptions
        self.observation_space = {
            "type": "dict",
            "properties": {
                "users": {
                    "type": "array",
                    "description": "List of users in the system",
                },
                "calendars": {"type": "array", "description": "List of calendars"},
                "events": {"type": "array", "description": "List of events"},
                "acls": {"type": "array", "description": "Calendar ACL entries"},
                "attendees": {"type": "array", "description": "Event attendees"},
                "step": {"type": "integer", "description": "Current step number"},
            },
        }

        self.action_space = {
            "type": "dict",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "create_event",
                        "update_event",
                        "delete_event",
                        "accept",
                        "decline",
                        "share_calendar",
                        "invite_user",
                    ],
                    "description": "Type of action to perform",
                },
                "params": {
                    "type": "object",
                    "description": "Action-specific parameters",
                },
            },
        }

    def reset(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Reset the environment to initial state.

        Args:
            seed: Random seed for reproducibility

        Returns:
            Initial observation dictionary
        """
        if seed is not None:
            random.seed(seed)

        # Close existing session if any
        if self.db:
            self.db.close()

        # Clear all tables
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        # Create new session
        self.db = self.SessionLocal()

        # Reset counters
        self.step_count = 0
        self.episode_reward = 0.0

        # Reset UI realism state
        self.popup_history = []
        self.color_assignments = {}

        # Initialize with some users
        self._create_initial_users()

        return self._get_observation()

    def _create_initial_users(self):
        """Create initial users for the environment."""
        user_names = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
        users = []

        for name in user_names:
            user = User(id=uuid4(), email=f"{name.lower()}@example.com", name=name)
            self.db.add(user)
            users.append(user)

        self.db.commit()

        # Create a calendar for each user
        for user in users:
            calendar = Calendar(
                id=uuid4(),
                title=f"{user.name}'s Calendar",
                timezone="UTC",
                owner_id=user.id,
                description=f"Primary calendar for {user.name}",
            )
            self.db.add(calendar)
            self.db.flush()

            # Create calendar list entry
            entry = CalendarListEntry(
                user_id=user.id, calendar_id=calendar.id, is_primary=True
            )
            self.db.add(entry)

        self.db.commit()

    def _get_observation(self) -> Dict[str, Any]:
        """
        Get current observation of the environment.

        Returns:
            Dictionary containing current state
        """
        # Get all users
        users = self.db.query(User).all()
        users_data = [
            {"id": str(user.id), "email": user.email, "name": user.name}
            for user in users
        ]

        # Get all calendars
        calendars = self.db.query(Calendar).all()
        calendars_data = [
            {
                "id": str(cal.id),
                "title": cal.title,
                "owner_id": str(cal.owner_id),
                "timezone": cal.timezone,
            }
            for cal in calendars
        ]

        # Get all events
        events = self.db.query(Event).all()
        events_data = [
            {
                "id": str(event.id),
                "calendar_id": str(event.calendar_id),
                "summary": event.summary,
                "start": event.start.isoformat() if event.start else None,
                "end": event.end.isoformat() if event.end else None,
                "status": event.status.value if event.status else None,
                "iCalUID": event.iCalUID,
            }
            for event in events
        ]

        # Get all ACLs
        acls = self.db.query(CalendarACL).all()
        acls_data = [
            {
                "id": acl.id,
                "calendar_id": str(acl.calendar_id),
                "grantee": acl.grantee,
                "role": acl.role.value,
            }
            for acl in acls
        ]

        # Get all attendees
        attendees = self.db.query(EventAttendee).all()
        attendees_data = [
            {
                "id": attendee.id,
                "event_id": str(attendee.event_id),
                "email": attendee.email,
                "response_status": attendee.response_status.value,
                "is_organizer": attendee.is_organizer,
            }
            for attendee in attendees
        ]

        return {
            "users": users_data,
            "calendars": calendars_data,
            "events": events_data,
            "acls": acls_data,
            "attendees": attendees_data,
            "step": self.step_count,
        }

    def step(
        self, action: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute an action in the environment.

        Args:
            action: Dictionary with 'type' and 'params'

        Returns:
            Tuple of (observation, reward, done, info)
        """
        self.step_count += 1

        action_type = action.get("type")
        params = action.get("params", {})

        reward = 0.0
        info = {"action": action_type, "success": False, "message": ""}

        try:
            if action_type == "create_event":
                reward = self._action_create_event(params, info)
            elif action_type == "update_event":
                reward = self._action_update_event(params, info)
            elif action_type == "delete_event":
                reward = self._action_delete_event(params, info)
            elif action_type == "accept":
                reward = self._action_accept_invitation(params, info)
            elif action_type == "decline":
                reward = self._action_decline_invitation(params, info)
            elif action_type == "share_calendar":
                reward = self._action_share_calendar(params, info)
            elif action_type == "invite_user":
                reward = self._action_invite_user(params, info)
            else:
                reward = 0.0
                info["message"] = f"Unknown action type: {action_type}"

        except Exception as e:
            reward = 0.0
            info["message"] = f"Error executing action: {str(e)}"

        self.episode_reward += reward

        # Check if episode is done
        done = self.step_count >= self.max_steps

        observation = self._get_observation()

        return observation, reward, done, info

    def _action_create_event(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Create an event action."""
        organizer_email = params.get("organizer_email")
        calendar_id = params.get("calendar_id")
        summary = params.get("summary", "New Event")
        start_offset_hours = params.get("start_offset_hours", 1)
        duration_hours = params.get("duration_hours", 1)
        attendees = params.get("attendees", [])

        if not organizer_email or not calendar_id:
            info["message"] = "Missing organizer_email or calendar_id"
            return 0.0

        # Convert calendar_id to UUID
        try:
            calendar_uuid = UUID(calendar_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid calendar_id format"
            return 0.0

        # Check if calendar exists
        calendar = self.db.query(Calendar).filter(Calendar.id == calendar_uuid).first()
        if not calendar:
            info["message"] = "Calendar not found"
            return 0.0

        # Create event payload
        start_time = datetime.now() + timedelta(hours=start_offset_hours)
        end_time = start_time + timedelta(hours=duration_hours)

        # Check for time conflicts
        conflicts = (
            self.db.query(Event)
            .filter(
                Event.calendar_id == calendar_uuid,
                Event.start < end_time,
                Event.end > start_time,
            )
            .count()
        )

        if conflicts > 0:
            info["message"] = "Time conflict detected"
            return 0.0

        payload = {
            "summary": summary,
            "start": start_time,
            "end": end_time,
            "attendees": [{"email": email} for email in attendees],
        }

        # Create event using service
        event = create_event(self.db, calendar_uuid, organizer_email, payload)

        info["success"] = True
        info["event_id"] = str(event.id)
        info["message"] = f"Event '{summary}' created successfully"

        # Binary reward: +1 for success
        return 1.0

    def _action_invite_user(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Invite user to existing event (not implemented in current service, placeholder)."""
        info["message"] = "Invite user action not yet implemented"
        info["success"] = False
        return 0.0

    def _action_accept_invitation(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Accept an event invitation."""
        event_id = params.get("event_id")
        attendee_email = params.get("attendee_email")

        if not event_id or not attendee_email:
            info["message"] = "Missing event_id or attendee_email"
            return 0.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return 0.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return 0.0

        # Check if attendee is on this event
        attendee = (
            self.db.query(EventAttendee)
            .filter(
                EventAttendee.event_id == event_uuid,
                EventAttendee.email == attendee_email,
            )
            .first()
        )

        if not attendee:
            info["message"] = "Attendee not found on this event"
            return 0.0

        # Update response
        update_attendee_response(
            self.db, event_uuid, attendee_email, AttendeeResponseStatus.ACCEPTED
        )

        info["success"] = True
        info["message"] = f"{attendee_email} accepted invitation"
        return 1.0

    def _action_decline_invitation(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Decline an event invitation."""
        event_id = params.get("event_id")
        attendee_email = params.get("attendee_email")

        if not event_id or not attendee_email:
            info["message"] = "Missing event_id or attendee_email"
            return 0.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return 0.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return 0.0

        # Check if attendee is on this event
        attendee = (
            self.db.query(EventAttendee)
            .filter(
                EventAttendee.event_id == event_uuid,
                EventAttendee.email == attendee_email,
            )
            .first()
        )

        if not attendee:
            info["message"] = "Attendee not found on this event"
            return 0.0

        # Update response
        update_attendee_response(
            self.db, event_uuid, attendee_email, AttendeeResponseStatus.DECLINED
        )

        info["success"] = True
        info["message"] = f"{attendee_email} declined invitation"
        return 1.0

    def _action_share_calendar(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Share calendar with another user."""
        calendar_id = params.get("calendar_id")
        grantee_email = params.get("grantee_email")
        role = params.get("role", "reader")

        if not calendar_id or not grantee_email:
            info["message"] = "Missing calendar_id or grantee_email"
            return 0.0

        try:
            calendar_uuid = UUID(calendar_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid calendar_id format"
            return 0.0

        # Check if calendar exists
        calendar = self.db.query(Calendar).filter(Calendar.id == calendar_uuid).first()
        if not calendar:
            info["message"] = "Calendar not found"
            return 0.0

        # Check if user exists
        user = self.db.query(User).filter(User.email == grantee_email).first()
        if not user:
            info["message"] = "User not found"
            return 0.0

        # Check if ACL already exists
        existing_acl = (
            self.db.query(CalendarACL)
            .filter(
                CalendarACL.calendar_id == calendar_uuid,
                CalendarACL.grantee == grantee_email,
            )
            .first()
        )

        if existing_acl:
            info["message"] = "ACL already exists"
            return 0.0

        # Convert role string to enum
        try:
            role_enum = CalendarRole(role)
        except ValueError:
            info["message"] = f"Invalid role: {role}"
            return 0.0

        # Create ACL
        acl = CalendarACL(
            calendar_id=calendar_uuid, grantee=grantee_email, role=role_enum
        )
        self.db.add(acl)
        self.db.commit()

        info["success"] = True
        info["message"] = f"Calendar shared with {grantee_email} as {role}"
        return 1.0

    def _action_update_event(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Update an existing event."""
        event_id = params.get("event_id")
        updates = params.get("updates", {})

        if not event_id:
            info["message"] = "Missing event_id"
            return 0.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return 0.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return 0.0

        # Update event using service
        update_event(self.db, event_uuid, updates)

        info["success"] = True
        info["message"] = "Event updated successfully"
        return 1.0

    def _action_delete_event(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Delete an existing event."""
        event_id = params.get("event_id")

        if not event_id:
            info["message"] = "Missing event_id"
            return 0.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return 0.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return 0.0

        # Delete the event (cascades to attendees)
        self.db.delete(event)
        self.db.commit()

        info["success"] = True
        info["message"] = "Event deleted successfully"
        return 1.0

    def _get_event_color(self, event_id: str) -> str:
        """
        Get consistent random color for an event from Google Calendar palette.

        Args:
            event_id: Event ID for consistent color assignment

        Returns:
            Hex color code
        """
        if not self.ui_realism:
            # Default blue if realism is off
            return "#4285f4"

        if event_id not in self.color_assignments:
            # Assign a random color from Google's palette
            color_name = random.choice(list(GOOGLE_CALENDAR_COLORS.keys()))
            self.color_assignments[event_id] = GOOGLE_CALENDAR_COLORS[color_name]

        return self.color_assignments[event_id]

    def _draw_popup(self, fig, ax, popup_type: str, scroll_offset: float):
        """
        Draw a UI popup overlay on the calendar screenshot.

        Args:
            fig: Matplotlib figure
            ax: Matplotlib axes
            popup_type: Type of popup to draw
            scroll_offset: Vertical scroll offset
        """
        if popup_type == "reminder_toast":
            # Toast notification at top-right
            toast_box = FancyBboxPatch(
                (0.68, 0.88 + scroll_offset),
                0.28,
                0.08,
                boxstyle="round,pad=0.01",
                facecolor="#323232",
                edgecolor="none",
                alpha=0.9,
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(toast_box)

            # Toast text
            fig.text(
                0.70,
                0.92 + scroll_offset,
                "🔔 Reminder: Meeting in 10 min",
                color="white",
                fontsize=9,
                weight="bold",
                transform=fig.transFigure,
                zorder=1001,
            )

        elif popup_type == "event_edit_modal":
            # Modal dialog in center
            modal_bg = Rectangle(
                (0, 0),
                1,
                1,
                facecolor="black",
                alpha=0.5,
                transform=fig.transFigure,
                zorder=999,
            )
            fig.patches.append(modal_bg)

            modal_box = FancyBboxPatch(
                (0.25, 0.3 + scroll_offset),
                0.5,
                0.4,
                boxstyle="round,pad=0.02",
                facecolor="white",
                edgecolor="#dadce0",
                linewidth=1,
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(modal_box)

            # Modal header
            fig.text(
                0.27,
                0.66 + scroll_offset,
                "Edit Event",
                color="#202124",
                fontsize=12,
                weight="bold",
                transform=fig.transFigure,
                zorder=1001,
            )

            # Modal content lines
            fig.text(
                0.27,
                0.58 + scroll_offset,
                "Title: ________________",
                color="#5f6368",
                fontsize=9,
                transform=fig.transFigure,
                zorder=1001,
            )
            fig.text(
                0.27,
                0.52 + scroll_offset,
                "Time: ________________",
                color="#5f6368",
                fontsize=9,
                transform=fig.transFigure,
                zorder=1001,
            )
            fig.text(
                0.27,
                0.46 + scroll_offset,
                "Location: ________________",
                color="#5f6368",
                fontsize=9,
                transform=fig.transFigure,
                zorder=1001,
            )

            # Buttons
            save_btn = FancyBboxPatch(
                (0.62, 0.33 + scroll_offset),
                0.08,
                0.04,
                boxstyle="round,pad=0.003",
                facecolor="#1a73e8",
                edgecolor="none",
                transform=fig.transFigure,
                zorder=1001,
            )
            fig.patches.append(save_btn)
            fig.text(
                0.64,
                0.35 + scroll_offset,
                "Save",
                color="white",
                fontsize=8,
                weight="bold",
                ha="center",
                transform=fig.transFigure,
                zorder=1002,
            )

        elif popup_type == "permission_error":
            # Error banner at top
            error_banner = Rectangle(
                (0, 0.92 + scroll_offset),
                1,
                0.06,
                facecolor="#d93025",
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(error_banner)

            fig.text(
                0.5,
                0.95 + scroll_offset,
                "⚠️ Permission denied: You don't have access to modify this event",
                color="white",
                fontsize=10,
                weight="bold",
                ha="center",
                transform=fig.transFigure,
                zorder=1001,
            )

        elif popup_type == "event_created_toast":
            # Success toast at bottom
            toast_box = FancyBboxPatch(
                (0.35, 0.08 + scroll_offset),
                0.3,
                0.06,
                boxstyle="round,pad=0.01",
                facecolor="#188038",
                edgecolor="none",
                alpha=0.95,
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(toast_box)

            fig.text(
                0.50,
                0.11 + scroll_offset,
                "✓ Event created",
                color="white",
                fontsize=10,
                weight="bold",
                ha="center",
                transform=fig.transFigure,
                zorder=1001,
            )

        elif popup_type == "sync_notification":
            # Syncing indicator at top-left
            sync_box = FancyBboxPatch(
                (0.02, 0.90 + scroll_offset),
                0.18,
                0.06,
                boxstyle="round,pad=0.01",
                facecolor="#e8f0fe",
                edgecolor="#1a73e8",
                linewidth=1,
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(sync_box)

            fig.text(
                0.04,
                0.93 + scroll_offset,
                "🔄 Syncing...",
                color="#1a73e8",
                fontsize=9,
                weight="bold",
                transform=fig.transFigure,
                zorder=1001,
            )

        elif popup_type == "calendar_shared_toast":
            # Info toast at bottom-right
            toast_box = FancyBboxPatch(
                (0.68, 0.08 + scroll_offset),
                0.28,
                0.08,
                boxstyle="round,pad=0.01",
                facecolor="#1a73e8",
                edgecolor="none",
                alpha=0.9,
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(toast_box)

            fig.text(
                0.70,
                0.12 + scroll_offset,
                "📅 Calendar shared with Bob",
                color="white",
                fontsize=9,
                weight="bold",
                transform=fig.transFigure,
                zorder=1001,
            )

        elif popup_type == "invitation_popup":
            # Small popup dialog
            popup_box = FancyBboxPatch(
                (0.60, 0.50 + scroll_offset),
                0.35,
                0.25,
                boxstyle="round,pad=0.015",
                facecolor="white",
                edgecolor="#dadce0",
                linewidth=2,
                transform=fig.transFigure,
                zorder=1000,
            )
            fig.patches.append(popup_box)

            fig.text(
                0.62,
                0.72 + scroll_offset,
                "New Invitation",
                color="#202124",
                fontsize=11,
                weight="bold",
                transform=fig.transFigure,
                zorder=1001,
            )

            fig.text(
                0.62,
                0.66 + scroll_offset,
                "Alice invited you to:",
                color="#5f6368",
                fontsize=9,
                transform=fig.transFigure,
                zorder=1001,
            )

            fig.text(
                0.62,
                0.62 + scroll_offset,
                '"Team Sync Meeting"',
                color="#202124",
                fontsize=9,
                weight="bold",
                transform=fig.transFigure,
                zorder=1001,
            )

            # Accept/Decline buttons
            accept_btn = FancyBboxPatch(
                (0.62, 0.53 + scroll_offset),
                0.10,
                0.04,
                boxstyle="round,pad=0.003",
                facecolor="#1a73e8",
                edgecolor="none",
                transform=fig.transFigure,
                zorder=1001,
            )
            fig.patches.append(accept_btn)
            fig.text(
                0.67,
                0.55 + scroll_offset,
                "Accept",
                color="white",
                fontsize=8,
                weight="bold",
                ha="center",
                transform=fig.transFigure,
                zorder=1002,
            )

            decline_btn = FancyBboxPatch(
                (0.74, 0.53 + scroll_offset),
                0.10,
                0.04,
                boxstyle="round,pad=0.003",
                facecolor="white",
                edgecolor="#dadce0",
                linewidth=1,
                transform=fig.transFigure,
                zorder=1001,
            )
            fig.patches.append(decline_btn)
            fig.text(
                0.79,
                0.55 + scroll_offset,
                "Decline",
                color="#5f6368",
                fontsize=8,
                weight="bold",
                ha="center",
                transform=fig.transFigure,
                zorder=1002,
            )

    def _get_popup_diversity_index(self) -> float:
        """
        Calculate popup diversity index (ratio of unique popup types shown).

        Returns:
            Float between 0 and 1 (1 = all popup types shown)
        """
        if not self.popup_history:
            return 0.0

        unique_popups = len(set(self.popup_history))
        total_popup_types = len(POPUP_TYPES)
        return unique_popups / total_popup_types

    def render_screenshot(self) -> str:
        """
        Generate a visual screenshot of the calendar state as base64 encoded image.

        With UI_REALISM enabled, adds:
        - Random popups (toasts, modals, errors)
        - Scroll offset variation (±10px)
        - Event color randomization from Google palette

        Returns:
            Base64 encoded PNG image
        """
        obs = self._get_observation()
        events = obs["events"]
        calendars = obs["calendars"]

        # UI Realism: Random scroll offset (±10 pixels in normalized coords)
        scroll_offset = 0.0
        if self.ui_realism:
            scroll_offset = random.uniform(-0.02, 0.02)  # ~±10px at 500px height

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor("white")

        if not events:
            # No events to display
            ax.text(
                0.5,
                0.5 + scroll_offset,
                "No events scheduled",
                ha="center",
                va="center",
                fontsize=16,
                color="gray",
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
        else:
            # Create calendar view with events
            now = datetime.now()

            # Group events by calendar
            calendar_events = {}
            for event in events:
                cal_id = event["calendar_id"]
                if cal_id not in calendar_events:
                    calendar_events[cal_id] = []
                calendar_events[cal_id].append(event)

            # Create timeline view
            y_pos = 0

            for i, (cal_id, cal_events) in enumerate(calendar_events.items()):
                # Find calendar name
                cal_name = next(
                    (c["title"] for c in calendars if c["id"] == cal_id), "Unknown"
                )

                # Plot events for this calendar
                for event in cal_events:
                    if event["start"] and event["end"]:
                        start = datetime.fromisoformat(event["start"])
                        end = datetime.fromisoformat(event["end"])

                        # Get event color (random if realism enabled)
                        color = self._get_event_color(event["id"])

                        # Draw event bar
                        ax.barh(
                            y_pos,
                            (end - start).total_seconds() / 3600,
                            left=mdates.date2num(start),
                            height=0.6,
                            color=color,
                            alpha=0.7,
                            edgecolor="black",
                            linewidth=1,
                        )

                        # Add event label
                        mid_time = start + (end - start) / 2
                        ax.text(
                            mdates.date2num(mid_time),
                            y_pos,
                            event["summary"][:20],
                            ha="center",
                            va="center",
                            fontsize=9,
                            fontweight="bold",
                        )

                # Add calendar label on y-axis
                ax.text(
                    mdates.date2num(now) - 0.5,
                    y_pos,
                    cal_name[:15],
                    ha="right",
                    va="center",
                    fontsize=10,
                )

                y_pos += 1

            # Format x-axis as time
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.xticks(rotation=45)

            ax.set_ylim(-0.5 + scroll_offset, y_pos - 0.5 + scroll_offset)
            ax.set_ylabel("Calendars")
            ax.set_xlabel("Time")

            # Title with popup diversity index if realism enabled
            title = (
                f"Google Calendar Gym - Step {self.step_count}/{self.max_steps} | "
                + f"Reward: {self.episode_reward:.1f} | Events: {len(events)}"
            )
            if self.ui_realism:
                diversity_idx = self._get_popup_diversity_index()
                title += f" | Popup Diversity: {diversity_idx:.2f}"

            ax.set_title(title, fontsize=12, fontweight="bold")
            ax.grid(True, alpha=0.3, axis="x")

        plt.tight_layout()

        # UI Realism: Add random popup overlay (30% chance)
        if self.ui_realism and random.random() < 0.3:
            popup_type = random.choice(POPUP_TYPES)
            self.popup_history.append(popup_type)
            self._draw_popup(fig, ax, popup_type, scroll_offset)

        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        return image_base64

    def close(self):
        """Clean up resources."""
        if self.db:
            self.db.close()
        self.engine.dispose()

    def render(self, mode: str = "human") -> Optional[str]:
        """
        Render the environment state.

        Args:
            mode: Render mode ('human' for text, 'ansi' for string)

        Returns:
            Optional string representation
        """
        obs = self._get_observation()

        output = f"""
=== Google Calendar Gym Environment ===
Step: {self.step_count}/{self.max_steps}
Episode Reward: {self.episode_reward:.2f}

Users: {len(obs['users'])}
Calendars: {len(obs['calendars'])}
Events: {len(obs['events'])}
ACLs: {len(obs['acls'])}
Attendees: {len(obs['attendees'])}
========================================
"""

        if mode == "ansi":
            return output
        elif mode == "human":
            print(output)
            return None
        else:
            return None
