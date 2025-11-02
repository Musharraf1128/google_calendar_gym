"""
Unit tests for Google Calendar Gym Environment.

Tests cover:
- Environment reset and initialization
- Action execution (create_event, accept, decline, share_calendar)
- Reward patterns
- State transitions
- Action sequences
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.gym.google_calendar_env import GoogleCalendarEnv
from app.models.models import AttendeeResponseStatus


@pytest.fixture
def env():
    """Create a fresh gym environment for each test."""
    environment = GoogleCalendarEnv()
    yield environment
    environment.close()


class TestEnvironmentBasics:
    """Test basic environment functionality."""

    def test_environment_initialization(self, env):
        """Test that environment initializes correctly."""
        assert env.step_count == 0
        assert env.max_steps == 100
        assert env.episode_reward == 0.0
        assert env.observation_space is not None
        assert env.action_space is not None

    def test_reset_creates_users(self, env):
        """Test that reset creates initial users."""
        obs = env.reset(seed=42)

        assert "users" in obs
        assert "calendars" in obs
        assert "events" in obs
        assert "step" in obs

        # Should create 5 initial users
        assert len(obs["users"]) == 5
        assert len(obs["calendars"]) == 5

        # Step should be 0 after reset
        assert obs["step"] == 0

    def test_reset_clears_state(self, env):
        """Test that reset clears previous state."""
        # First reset
        obs1 = env.reset(seed=42)
        user_count_1 = len(obs1["users"])

        # Take some steps
        env.step_count = 10
        env.episode_reward = 5.0

        # Reset again
        obs2 = env.reset(seed=42)

        assert env.step_count == 0
        assert env.episode_reward == 0.0
        assert len(obs2["users"]) == user_count_1

    def test_observation_structure(self, env):
        """Test that observation has correct structure."""
        obs = env.reset()

        assert isinstance(obs, dict)
        assert "users" in obs
        assert "calendars" in obs
        assert "events" in obs
        assert "acls" in obs
        assert "attendees" in obs
        assert "step" in obs

        # Each should be a list
        assert isinstance(obs["users"], list)
        assert isinstance(obs["calendars"], list)
        assert isinstance(obs["events"], list)


class TestCreateEventAction:
    """Test event creation actions."""

    def test_create_event_success(self, env):
        """Test successful event creation."""
        obs = env.reset(seed=42)

        # Get first user and their calendar
        user = obs["users"][0]
        calendar = obs["calendars"][0]

        action = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": calendar["id"],
                "summary": "Team Meeting",
                "start_offset_hours": 2,
                "duration_hours": 1,
                "attendees": [],
            },
        }

        obs, reward, done, info = env.step(action)

        # Should get positive reward
        assert reward == 1.0
        assert info["success"] is True
        assert "event_id" in info

        # Should have one event now
        assert len(obs["events"]) == 1
        assert obs["events"][0]["summary"] == "Team Meeting"

    def test_create_event_with_attendees(self, env):
        """Test creating event with attendees gives bonus reward."""
        obs = env.reset(seed=42)

        user = obs["users"][0]
        calendar = obs["calendars"][0]
        attendee1 = obs["users"][1]["email"]
        attendee2 = obs["users"][2]["email"]

        action = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": calendar["id"],
                "summary": "Big Meeting",
                "start_offset_hours": 2,
                "duration_hours": 1,
                "attendees": [attendee1, attendee2],
            },
        }

        obs, reward, done, info = env.step(action)

        # Base reward (1.0) + attendee bonus (0.5 * 2)
        assert reward == 2.0
        assert info["success"] is True

        # Should have attendees
        assert len(obs["attendees"]) > 0

    def test_create_event_time_conflict(self, env):
        """Test that time conflicts result in negative reward."""
        obs = env.reset(seed=42)

        user = obs["users"][0]
        calendar = obs["calendars"][0]

        # Create first event
        action1 = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": calendar["id"],
                "summary": "Event 1",
                "start_offset_hours": 2,
                "duration_hours": 2,
            },
        }

        env.step(action1)

        # Create conflicting event
        action2 = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": calendar["id"],
                "summary": "Event 2",
                "start_offset_hours": 2,  # Same start time
                "duration_hours": 1,
            },
        }

        obs, reward, done, info = env.step(action2)

        # Should get negative reward for conflict
        assert reward == -2.0
        assert info["success"] is False
        assert "conflict" in info["message"].lower()

    def test_create_event_invalid_calendar(self, env):
        """Test creating event with invalid calendar ID."""
        obs = env.reset()

        user = obs["users"][0]

        action = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": str(uuid4()),  # Non-existent calendar
                "summary": "Invalid Event",
            },
        }

        obs, reward, done, info = env.step(action)

        # Should get negative reward
        assert reward == -1.0
        assert info["success"] is False


class TestAttendeeActions:
    """Test attendee response actions."""

    def test_accept_invitation(self, env):
        """Test accepting an event invitation."""
        obs = env.reset(seed=42)

        # Create event with attendees
        organizer = obs["users"][0]
        calendar = obs["calendars"][0]
        attendee_email = obs["users"][1]["email"]

        create_action = {
            "type": "create_event",
            "params": {
                "organizer_email": organizer["email"],
                "calendar_id": calendar["id"],
                "summary": "Meeting",
                "start_offset_hours": 2,
                "duration_hours": 1,
                "attendees": [attendee_email],
            },
        }

        obs, _, _, info = env.step(create_action)
        event_id = info["event_id"]

        # Accept invitation
        accept_action = {
            "type": "accept",
            "params": {"event_id": event_id, "attendee_email": attendee_email},
        }

        obs, reward, done, info = env.step(accept_action)

        # Should get positive reward
        assert reward == 1.0
        assert info["success"] is True

        # Check attendee status updated
        attendees = [a for a in obs["attendees"] if a["email"] == attendee_email]
        assert len(attendees) > 0
        assert attendees[0]["response_status"] == "accepted"

    def test_decline_invitation(self, env):
        """Test declining an event invitation."""
        obs = env.reset(seed=42)

        # Create event with attendees
        organizer = obs["users"][0]
        calendar = obs["calendars"][0]
        attendee_email = obs["users"][1]["email"]

        create_action = {
            "type": "create_event",
            "params": {
                "organizer_email": organizer["email"],
                "calendar_id": calendar["id"],
                "summary": "Meeting",
                "start_offset_hours": 2,
                "duration_hours": 1,
                "attendees": [attendee_email],
            },
        }

        obs, _, _, info = env.step(create_action)
        event_id = info["event_id"]

        # Decline invitation
        decline_action = {
            "type": "decline",
            "params": {"event_id": event_id, "attendee_email": attendee_email},
        }

        obs, reward, done, info = env.step(decline_action)

        # Should get negative reward
        assert reward == -0.5
        assert info["success"] is True

        # Check attendee status updated
        attendees = [a for a in obs["attendees"] if a["email"] == attendee_email]
        assert len(attendees) > 0
        assert attendees[0]["response_status"] == "declined"

    def test_accept_invalid_event(self, env):
        """Test accepting non-existent event."""
        env.reset()

        action = {
            "type": "accept",
            "params": {"event_id": str(uuid4()), "attendee_email": "test@example.com"},
        }

        obs, reward, done, info = env.step(action)

        assert reward == -1.0
        assert info["success"] is False


class TestCalendarSharing:
    """Test calendar sharing actions."""

    def test_share_calendar_success(self, env):
        """Test successful calendar sharing."""
        obs = env.reset(seed=42)

        calendar = obs["calendars"][0]
        grantee = obs["users"][1]

        action = {
            "type": "share_calendar",
            "params": {
                "calendar_id": calendar["id"],
                "grantee_email": grantee["email"],
                "role": "reader",
            },
        }

        obs, reward, done, info = env.step(action)

        # Should get positive reward
        assert reward == 1.0
        assert info["success"] is True

        # Should have ACL entry
        assert len(obs["acls"]) == 1
        assert obs["acls"][0]["grantee"] == grantee["email"]
        assert obs["acls"][0]["role"] == "reader"

    def test_share_calendar_duplicate(self, env):
        """Test sharing calendar with same user twice."""
        obs = env.reset(seed=42)

        calendar = obs["calendars"][0]
        grantee = obs["users"][1]

        action = {
            "type": "share_calendar",
            "params": {
                "calendar_id": calendar["id"],
                "grantee_email": grantee["email"],
                "role": "reader",
            },
        }

        # First share - should succeed
        env.step(action)

        # Second share - should fail
        obs, reward, done, info = env.step(action)

        assert reward == -0.5
        assert info["success"] is False

    def test_share_calendar_invalid_role(self, env):
        """Test sharing with invalid role."""
        obs = env.reset()

        calendar = obs["calendars"][0]
        grantee = obs["users"][1]

        action = {
            "type": "share_calendar",
            "params": {
                "calendar_id": calendar["id"],
                "grantee_email": grantee["email"],
                "role": "invalid_role",
            },
        }

        obs, reward, done, info = env.step(action)

        assert reward == -1.0
        assert info["success"] is False


class TestActionSequences:
    """Test sequences of actions to verify state transitions."""

    def test_complete_event_lifecycle(self, env):
        """Test complete event lifecycle: create, invite, accept, update."""
        obs = env.reset(seed=42)
        total_reward = 0.0

        # Step 1: Create event with attendees
        organizer = obs["users"][0]
        calendar = obs["calendars"][0]
        attendee1 = obs["users"][1]["email"]
        attendee2 = obs["users"][2]["email"]

        create_action = {
            "type": "create_event",
            "params": {
                "organizer_email": organizer["email"],
                "calendar_id": calendar["id"],
                "summary": "Project Kickoff",
                "start_offset_hours": 24,
                "duration_hours": 2,
                "attendees": [attendee1, attendee2],
            },
        }

        obs, reward, done, info = env.step(create_action)
        total_reward += reward
        event_id = info["event_id"]

        assert reward == 2.0  # 1.0 base + 2 * 0.5 for attendees
        assert len(obs["events"]) >= 1

        # Step 2: First attendee accepts
        accept_action1 = {
            "type": "accept",
            "params": {"event_id": event_id, "attendee_email": attendee1},
        }

        obs, reward, done, info = env.step(accept_action1)
        total_reward += reward

        assert reward == 1.0
        assert info["success"] is True

        # Step 3: Second attendee declines
        decline_action = {
            "type": "decline",
            "params": {"event_id": event_id, "attendee_email": attendee2},
        }

        obs, reward, done, info = env.step(decline_action)
        total_reward += reward

        assert reward == -0.5

        # Step 4: Update event
        update_action = {
            "type": "update_event",
            "params": {
                "event_id": event_id,
                "updates": {"summary": "Updated Project Kickoff"},
            },
        }

        obs, reward, done, info = env.step(update_action)
        total_reward += reward

        assert reward == 0.3
        assert info["success"] is True

        # Total reward should be positive
        assert total_reward == 2.8  # 2.0 + 1.0 - 0.5 + 0.3

    def test_multi_calendar_collaboration(self, env):
        """Test collaboration across multiple calendars."""
        obs = env.reset(seed=42)
        total_reward = 0.0

        user1 = obs["users"][0]
        user2 = obs["users"][1]
        calendar1 = obs["calendars"][0]
        calendar2 = obs["calendars"][1]

        # User 1 shares calendar with User 2
        share_action = {
            "type": "share_calendar",
            "params": {
                "calendar_id": calendar1["id"],
                "grantee_email": user2["email"],
                "role": "writer",
            },
        }

        obs, reward, done, info = env.step(share_action)
        total_reward += reward

        assert reward == 1.0

        # Create events on both calendars
        for i, (user, calendar) in enumerate([(user1, calendar1), (user2, calendar2)]):
            create_action = {
                "type": "create_event",
                "params": {
                    "organizer_email": user["email"],
                    "calendar_id": calendar["id"],
                    "summary": f"Event {i+1}",
                    "start_offset_hours": (i + 1) * 2,
                    "duration_hours": 1,
                },
            }

            obs, reward, done, info = env.step(create_action)
            total_reward += reward

            assert reward == 1.0

        # Should have 2 events and 1 ACL
        assert len(obs["events"]) >= 2
        assert len(obs["acls"]) >= 1
        assert total_reward == 3.0


class TestRewardPatterns:
    """Test reward patterns to ensure they make sense."""

    def test_positive_rewards_for_successful_actions(self, env):
        """Test that successful actions give positive rewards."""
        obs = env.reset(seed=42)
        positive_rewards = []

        user = obs["users"][0]
        calendar = obs["calendars"][0]

        # Create event - should be positive
        create_action = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": calendar["id"],
                "summary": "Meeting",
            },
        }

        obs, reward, done, info = env.step(create_action)
        assert reward > 0
        positive_rewards.append(reward)

        # Share calendar - should be positive
        share_action = {
            "type": "share_calendar",
            "params": {
                "calendar_id": calendar["id"],
                "grantee_email": obs["users"][1]["email"],
                "role": "reader",
            },
        }

        obs, reward, done, info = env.step(share_action)
        assert reward > 0
        positive_rewards.append(reward)

        assert all(r > 0 for r in positive_rewards)

    def test_negative_rewards_for_errors(self, env):
        """Test that errors give negative rewards."""
        obs = env.reset()

        # Invalid action type
        invalid_action = {"type": "invalid_action", "params": {}}

        obs, reward, done, info = env.step(invalid_action)
        assert reward == -1.0

    def test_episode_done_after_max_steps(self, env):
        """Test that episode ends after max_steps."""
        env.reset()
        env.max_steps = 5

        done = False
        for i in range(10):
            obs, reward, done, info = env.step({"type": "unknown", "params": {}})

            # step_count increments before checking done, so:
            # i=0 -> step_count=1, done=False
            # i=1 -> step_count=2, done=False
            # i=2 -> step_count=3, done=False
            # i=3 -> step_count=4, done=False
            # i=4 -> step_count=5, done=True (reached max_steps)
            if i < 4:
                assert done is False, f"Episode should not be done at step {i+1}"
            else:
                assert done is True, f"Episode should be done at step {i+1}"
                break


class TestEnvironmentRender:
    """Test environment rendering."""

    def test_render_returns_string(self, env):
        """Test that render returns string representation."""
        env.reset()

        output = env.render(mode="ansi")

        assert isinstance(output, str)
        assert "Google Calendar Gym Environment" in output
        assert "Step:" in output
        assert "Episode Reward:" in output

    def test_render_human_mode(self, env):
        """Test human render mode prints to stdout."""
        env.reset()

        # Should return None but print to stdout
        result = env.render(mode="human")
        assert result is None
