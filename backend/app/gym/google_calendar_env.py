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
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

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
        - type: Action type (create_event, invite_user, accept, decline, share_calendar, update_event)
        - params: Action-specific parameters

    Reward Function:
        - Successful event creation: +1.0
        - Successful invitation: +0.5
        - Attendee accepts: +1.0
        - Attendee declines: -0.5
        - Calendar sharing: +1.0
        - Event update: +0.3
        - Invalid action: -1.0
        - Time conflict: -2.0
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
                        "invite_user",
                        "accept",
                        "decline",
                        "share_calendar",
                        "update_event",
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
            elif action_type == "invite_user":
                reward = self._action_invite_user(params, info)
            elif action_type == "accept":
                reward = self._action_accept_invitation(params, info)
            elif action_type == "decline":
                reward = self._action_decline_invitation(params, info)
            elif action_type == "share_calendar":
                reward = self._action_share_calendar(params, info)
            elif action_type == "update_event":
                reward = self._action_update_event(params, info)
            else:
                reward = -1.0
                info["message"] = f"Unknown action type: {action_type}"

        except Exception as e:
            reward = -1.0
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
            return -1.0

        # Convert calendar_id to UUID
        try:
            calendar_uuid = UUID(calendar_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid calendar_id format"
            return -1.0

        # Check if calendar exists
        calendar = self.db.query(Calendar).filter(Calendar.id == calendar_uuid).first()
        if not calendar:
            info["message"] = "Calendar not found"
            return -1.0

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
            return -2.0

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

        # Base reward + bonus for attendees
        reward = 1.0 + (0.5 * len(attendees))
        return reward

    def _action_invite_user(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Invite user to existing event (not implemented in current service, placeholder)."""
        info["message"] = "Invite user action not yet implemented"
        info["success"] = False
        return -0.5

    def _action_accept_invitation(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Accept an event invitation."""
        event_id = params.get("event_id")
        attendee_email = params.get("attendee_email")

        if not event_id or not attendee_email:
            info["message"] = "Missing event_id or attendee_email"
            return -1.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return -1.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return -1.0

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
            return -1.0

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
            return -1.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return -1.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return -1.0

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
            return -1.0

        # Update response
        update_attendee_response(
            self.db, event_uuid, attendee_email, AttendeeResponseStatus.DECLINED
        )

        info["success"] = True
        info["message"] = f"{attendee_email} declined invitation"
        return -0.5

    def _action_share_calendar(
        self, params: Dict[str, Any], info: Dict[str, Any]
    ) -> float:
        """Share calendar with another user."""
        calendar_id = params.get("calendar_id")
        grantee_email = params.get("grantee_email")
        role = params.get("role", "reader")

        if not calendar_id or not grantee_email:
            info["message"] = "Missing calendar_id or grantee_email"
            return -1.0

        try:
            calendar_uuid = UUID(calendar_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid calendar_id format"
            return -1.0

        # Check if calendar exists
        calendar = self.db.query(Calendar).filter(Calendar.id == calendar_uuid).first()
        if not calendar:
            info["message"] = "Calendar not found"
            return -1.0

        # Check if user exists
        user = self.db.query(User).filter(User.email == grantee_email).first()
        if not user:
            info["message"] = "User not found"
            return -1.0

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
            return -0.5

        # Convert role string to enum
        try:
            role_enum = CalendarRole(role)
        except ValueError:
            info["message"] = f"Invalid role: {role}"
            return -1.0

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
            return -1.0

        try:
            event_uuid = UUID(event_id)
        except (ValueError, AttributeError):
            info["message"] = "Invalid event_id format"
            return -1.0

        # Check if event exists
        event = self.db.query(Event).filter(Event.id == event_uuid).first()
        if not event:
            info["message"] = "Event not found"
            return -1.0

        # Update event using service
        update_event(self.db, event_uuid, updates)

        info["success"] = True
        info["message"] = "Event updated successfully"
        return 0.3

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
