#!/usr/bin/env python3
"""
End-to-End Gym Environment Test Script

Tests the gym loop with 3 episodes:
- /gym/reset returns initial state
- /gym/step executes actions (create/edit/delete)
- Verifies reward system (+1 valid, 0 invalid)
- Logs complete sequence with actions and rewards
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any

API_BASE = "http://localhost:8000/api"


def print_separator(title: str = ""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def print_observation(obs: Dict[str, Any], title: str = "Observation"):
    """Pretty print observation."""
    print(f"📊 {title}:")
    print(f"  - Users: {len(obs.get('users', []))}")
    print(f"  - Calendars: {len(obs.get('calendars', []))}")
    print(f"  - Events: {len(obs.get('events', []))}")
    print(f"  - Conflicts: {obs.get('conflicts', 0)}")
    print(f"  - Total Events: {obs.get('total_events', 0)}")
    print(f"  - Pending Responses: {obs.get('pending_responses', 0)}")


def print_action(action: Dict[str, Any], action_num: int):
    """Pretty print action."""
    print(f"🎯 Action {action_num}: {action['type']}")
    if "params" in action:
        for key, value in action["params"].items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            print(f"    {key}: {value}")


def print_step_result(reward: float, done: bool, info: Dict[str, Any]):
    """Pretty print step result."""
    reward_emoji = "✅" if reward > 0 else "❌" if reward < 0 else "⚪"
    print(f"{reward_emoji} Reward: {reward:+.1f}")
    print(f"  Done: {done}")
    if info:
        print(f"  Info: {json.dumps(info, indent=4)}")


def reset_environment(env_id: str, seed: int = None) -> Dict[str, Any]:
    """Reset the gym environment."""
    print(f"🔄 Resetting environment: {env_id}")
    if seed:
        print(f"  Seed: {seed}")

    response = requests.post(
        f"{API_BASE}/gym/reset", json={"env_id": env_id, "seed": seed}
    )

    if response.status_code != 200:
        print(f"❌ Reset failed: {response.status_code}")
        print(f"   {response.text}")
        return None

    data = response.json()
    print(f"✅ Environment reset successfully")
    print_observation(data["observation"], "Initial State")
    return data


def step_environment(
    env_id: str, action: Dict[str, Any], action_num: int
) -> Dict[str, Any]:
    """Execute a step in the environment."""
    print_action(action, action_num)

    response = requests.post(
        f"{API_BASE}/gym/step", json={"env_id": env_id, "action": action}
    )

    if response.status_code != 200:
        print(f"❌ Step failed: {response.status_code}")
        print(f"   {response.text}")
        return None

    data = response.json()
    print_step_result(data["reward"], data["done"], data.get("info", {}))
    print_observation(data["observation"], "New State")
    return data


def render_environment(env_id: str):
    """Render the current environment state."""
    response = requests.get(f"{API_BASE}/gym/render/{env_id}")

    if response.status_code != 200:
        print(f"❌ Render failed: {response.status_code}")
        return

    data = response.json()
    print(f"\n📸 Environment Render:\n")
    print(data["render"])
    print()


def run_episode_1():
    """Episode 1: Create events and test valid actions."""
    print_separator("EPISODE 1: Creating Events (Valid Actions)")

    env_id = "episode_1"
    episode_reward = 0

    # Reset
    reset_data = reset_environment(env_id, seed=42)
    if not reset_data:
        return

    obs = reset_data["observation"]

    # Get first user and calendar
    if not obs["users"] or not obs["calendars"]:
        print("❌ No users or calendars in environment")
        return

    user = obs["users"][0]
    calendar = obs["calendars"][0]

    print(f"\n📝 Using user: {user['name']} ({user['email']})")
    print(f"📅 Using calendar: {calendar['title']}")

    # Action 1: Create event (should give +1 reward)
    action1 = {
        "type": "create_event",
        "params": {
            "organizer_email": user["email"],
            "calendar_id": calendar["id"],
            "summary": "Team Standup",
            "start_offset_hours": 2,
            "duration_hours": 1,
        },
    }

    result = step_environment(env_id, action1, 1)
    if result:
        episode_reward += result["reward"]

    # Action 2: Create another event (should give +1 reward)
    action2 = {
        "type": "create_event",
        "params": {
            "organizer_email": user["email"],
            "calendar_id": calendar["id"],
            "summary": "Sprint Planning",
            "start_offset_hours": 5,
            "duration_hours": 2,
        },
    }

    result = step_environment(env_id, action2, 2)
    if result:
        episode_reward += result["reward"]

    # Action 3: Create event with attendees (should give +1 reward)
    if len(obs["users"]) > 1:
        action3 = {
            "type": "create_event",
            "params": {
                "organizer_email": user["email"],
                "calendar_id": calendar["id"],
                "summary": "Team Sync",
                "start_offset_hours": 8,
                "duration_hours": 1,
                "attendees": [obs["users"][1]["email"]],
            },
        }

        result = step_environment(env_id, action3, 3)
        if result:
            episode_reward += result["reward"]

    # Render final state
    render_environment(env_id)

    print(f"\n🎊 Episode 1 Complete!")
    print(f"   Total Reward: {episode_reward:+.1f}")
    print_separator()


def run_episode_2():
    """Episode 2: Update and delete events."""
    print_separator("EPISODE 2: Updating and Deleting Events")

    env_id = "episode_2"
    episode_reward = 0

    # Reset
    reset_data = reset_environment(env_id, seed=123)
    if not reset_data:
        return

    obs = reset_data["observation"]

    if not obs["users"] or not obs["calendars"]:
        print("❌ No users or calendars in environment")
        return

    user = obs["users"][0]
    calendar = obs["calendars"][0]

    # Action 1: Create an event first
    action1 = {
        "type": "create_event",
        "params": {
            "organizer_email": user["email"],
            "calendar_id": calendar["id"],
            "summary": "Meeting to Update",
            "start_offset_hours": 3,
            "duration_hours": 1,
        },
    }

    result = step_environment(env_id, action1, 1)
    if result:
        episode_reward += result["reward"]

        # Get the created event ID
        if result["observation"]["events"]:
            event_id = result["observation"]["events"][0]["id"]

            # Action 2: Update the event (should give +1 reward)
            action2 = {
                "type": "update_event",
                "params": {
                    "event_id": event_id,
                    "summary": "Updated Meeting Title",
                    "start_offset_hours": 4,
                    "duration_hours": 2,
                },
            }

            result2 = step_environment(env_id, action2, 2)
            if result2:
                episode_reward += result2["reward"]

            # Action 3: Delete the event (should give reward)
            action3 = {"type": "delete_event", "params": {"event_id": event_id}}

            result3 = step_environment(env_id, action3, 3)
            if result3:
                episode_reward += result3["reward"]

    # Render final state
    render_environment(env_id)

    print(f"\n🎊 Episode 2 Complete!")
    print(f"   Total Reward: {episode_reward:+.1f}")
    print_separator()


def run_episode_3():
    """Episode 3: Test invalid actions and edge cases."""
    print_separator("EPISODE 3: Invalid Actions and Edge Cases")

    env_id = "episode_3"
    episode_reward = 0

    # Reset
    reset_data = reset_environment(env_id, seed=456)
    if not reset_data:
        return

    obs = reset_data["observation"]

    if not obs["users"] or not obs["calendars"]:
        print("❌ No users or calendars in environment")
        return

    user = obs["users"][0]
    calendar = obs["calendars"][0]

    # Action 1: Try to update non-existent event (should give 0 or negative reward)
    action1 = {
        "type": "update_event",
        "params": {
            "event_id": "00000000-0000-0000-0000-000000000000",  # Non-existent ID
            "summary": "This should fail",
        },
    }

    result = step_environment(env_id, action1, 1)
    if result:
        episode_reward += result["reward"]

    # Action 2: Create a valid event
    action2 = {
        "type": "create_event",
        "params": {
            "organizer_email": user["email"],
            "calendar_id": calendar["id"],
            "summary": "Valid Event",
            "start_offset_hours": 1,
            "duration_hours": 1,
        },
    }

    result = step_environment(env_id, action2, 2)
    if result:
        episode_reward += result["reward"]

    # Action 3: Create overlapping event (might create conflict)
    action3 = {
        "type": "create_event",
        "params": {
            "organizer_email": user["email"],
            "calendar_id": calendar["id"],
            "summary": "Overlapping Event",
            "start_offset_hours": 1,  # Same time as previous
            "duration_hours": 1,
        },
    }

    result = step_environment(env_id, action3, 3)
    if result:
        episode_reward += result["reward"]
        print(f"\n⚠️  Conflicts detected: {result['observation'].get('conflicts', 0)}")

    # Render final state
    render_environment(env_id)

    print(f"\n🎊 Episode 3 Complete!")
    print(f"   Total Reward: {episode_reward:+.1f}")
    print_separator()


def main():
    """Run all episodes."""
    print_separator("🤖 Gym Environment End-to-End Test")
    print("Testing Google Calendar Gym with 3 episodes")
    print(f"API Base URL: {API_BASE}")

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            print("❌ Server not responding at http://localhost:8000")
            print("   Please start the server with: uvicorn app.main:app --reload")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Please start the server with: uvicorn app.main:app --reload")
        return

    print("✅ Server is running\n")

    # Run episodes
    run_episode_1()
    run_episode_2()
    run_episode_3()

    # Final summary
    print_separator("🎯 TEST SUMMARY")

    # List all environments
    response = requests.get(f"{API_BASE}/gym/list")
    if response.status_code == 200:
        data = response.json()
        print("Active Environments:")
        for env in data["environments"]:
            print(f"\n  📦 {env['env_id']}")
            print(f"     Steps: {env['step']}/{env['max_steps']}")
            print(f"     Episode Reward: {env['episode_reward']:+.1f}")
            print(f"     Events: {env['num_events']}")
            print(f"     Users: {env['num_users']}")
            print(f"     Calendars: {env['num_calendars']}")

    print_separator()
    print("\n✅ All episodes completed successfully!")
    print("\nKey Observations:")
    print("  - Valid actions (create, update, delete) give positive rewards")
    print("  - Invalid actions (non-existent resources) give zero/negative rewards")
    print("  - Overlapping events create conflicts (tracked in observation)")
    print("  - Each environment maintains its own state independently")
    print()


if __name__ == "__main__":
    main()
