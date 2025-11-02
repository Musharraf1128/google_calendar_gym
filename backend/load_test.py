#!/usr/bin/env python3
"""
Load Test for Google Calendar Gym API

Tests:
- 50 concurrent users
- 1000 total events created
- Measures p95 latency (target: < 300ms)
- Verifies DB commit consistency
- Outputs JSON summary
"""

import requests
import time
import threading
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

API_BASE = "http://localhost:8000/api"
CONCURRENT_USERS = 50
TOTAL_EVENTS = 1000
EVENTS_PER_USER = TOTAL_EVENTS // CONCURRENT_USERS


# Thread-safe metrics storage
class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.latencies = []
        self.failed_requests = 0
        self.successful_requests = 0
        self.events_created = []
        self.errors = defaultdict(int)

    def add_latency(self, latency: float):
        with self.lock:
            self.latencies.append(latency)

    def add_success(self, event_id: str):
        with self.lock:
            self.successful_requests += 1
            self.events_created.append(event_id)

    def add_failure(self, error_msg: str):
        with self.lock:
            self.failed_requests += 1
            self.errors[error_msg] += 1

    def get_summary(self) -> Dict[str, Any]:
        with self.lock:
            if not self.latencies:
                return {
                    "avg_latency": 0,
                    "p95_latency": 0,
                    "p99_latency": 0,
                    "min_latency": 0,
                    "max_latency": 0,
                    "failed_requests": self.failed_requests,
                    "successful_requests": self.successful_requests,
                    "total_requests": self.failed_requests + self.successful_requests,
                    "events_created": len(self.events_created),
                    "unique_events": len(set(self.events_created)),
                    "errors": dict(self.errors),
                }

            latencies_array = np.array(self.latencies)
            return {
                "avg_latency": float(np.mean(latencies_array)),
                "p95_latency": float(np.percentile(latencies_array, 95)),
                "p99_latency": float(np.percentile(latencies_array, 99)),
                "min_latency": float(np.min(latencies_array)),
                "max_latency": float(np.max(latencies_array)),
                "failed_requests": self.failed_requests,
                "successful_requests": self.successful_requests,
                "total_requests": self.failed_requests + self.successful_requests,
                "events_created": len(self.events_created),
                "unique_events": len(set(self.events_created)),
                "errors": dict(self.errors),
            }


metrics = Metrics()


def setup_test_data():
    """Create test users and calendars."""
    print("🔧 Setting up test data...")

    # Get existing users
    try:
        response = requests.get(f"{API_BASE}/users", timeout=5)
        if response.status_code == 200:
            users = response.json()
            print(f"   Found {len(users)} existing users")
            return users
    except Exception as e:
        print(f"   ⚠️  Could not fetch users: {e}")

    return []


def create_event_worker(user_id: int, user_data: Dict[str, Any], events_to_create: int):
    """
    Worker thread that creates events for a specific user.

    Args:
        user_id: Worker ID (0-49)
        user_data: User information including email and calendar_id
        events_to_create: Number of events this worker should create
    """
    user_email = user_data["email"]
    calendar_id = user_data["calendar_id"]

    for i in range(events_to_create):
        # Create unique event
        event_data = {
            "organizer_email": user_email,
            "calendar_id": calendar_id,
            "summary": f"Load Test Event U{user_id}-E{i}",
            "start_offset_hours": 1 + (i * 0.5),  # Stagger events to avoid conflicts
            "duration_hours": 0.25,  # 15 minute events
        }

        action = {"type": "create_event", "params": event_data}

        # Measure latency
        start_time = time.time()

        try:
            response = requests.post(
                f"{API_BASE}/gym/step",
                json={"env_id": f"load_test_user_{user_id}", "action": action},
                timeout=10,
            )

            latency = (time.time() - start_time) * 1000  # Convert to ms
            metrics.add_latency(latency)

            if response.status_code == 200:
                data = response.json()
                if data.get("info", {}).get("success"):
                    event_id = data["info"].get("event_id", "unknown")
                    metrics.add_success(event_id)
                else:
                    error_msg = data.get("info", {}).get("message", "Unknown error")
                    metrics.add_failure(f"Action failed: {error_msg}")
            else:
                metrics.add_failure(f"HTTP {response.status_code}")

        except requests.Timeout:
            latency = (time.time() - start_time) * 1000
            metrics.add_latency(latency)
            metrics.add_failure("Timeout")
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            metrics.add_latency(latency)
            metrics.add_failure(f"Exception: {str(e)}")


def initialize_environments():
    """Initialize gym environments for all concurrent users."""
    print(f"🚀 Initializing {CONCURRENT_USERS} gym environments...")

    users = setup_test_data()

    if len(users) < 5:
        print("   ⚠️  Not enough users in database. Need at least 5 users.")
        return []

    user_configs = []

    # Initialize each environment
    for i in range(CONCURRENT_USERS):
        user = users[i % len(users)]  # Cycle through available users

        try:
            response = requests.post(
                f"{API_BASE}/gym/reset",
                json={"env_id": f"load_test_user_{i}", "seed": i},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                obs = data["observation"]

                if obs["users"] and obs["calendars"]:
                    user_configs.append(
                        {
                            "user_id": i,
                            "email": obs["users"][0]["email"],
                            "calendar_id": obs["calendars"][0]["id"],
                        }
                    )
            else:
                print(
                    f"   ⚠️  Failed to initialize env {i}: HTTP {response.status_code}"
                )

        except Exception as e:
            print(f"   ⚠️  Failed to initialize env {i}: {e}")

    print(f"   ✅ Initialized {len(user_configs)} environments")
    return user_configs


def verify_db_consistency():
    """Verify that all events were committed to database."""
    print("\n🔍 Verifying DB consistency...")

    # Query each environment to check event count
    total_db_events = 0
    env_counts = []

    try:
        response = requests.get(f"{API_BASE}/gym/list", timeout=10)
        if response.status_code == 200:
            data = response.json()
            environments = data.get("environments", [])

            for env in environments:
                if env["env_id"].startswith("load_test_user_"):
                    num_events = env.get("num_events", 0)
                    total_db_events += num_events
                    env_counts.append(num_events)

            print(f"   Total events in DB: {total_db_events}")
            print(f"   Events created per env (sample): {env_counts[:5]}")

            # Check consistency
            expected = metrics.successful_requests
            if total_db_events == expected:
                print(f"   ✅ DB consistency verified: {total_db_events} events")
                return True
            else:
                print(f"   ⚠️  Mismatch: Expected {expected}, Found {total_db_events}")
                return False

    except Exception as e:
        print(f"   ❌ Failed to verify DB: {e}")
        return False


def run_load_test():
    """Execute the load test with concurrent users."""
    print("\n" + "=" * 80)
    print("🚀 GOOGLE CALENDAR GYM - LOAD TEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  - Concurrent Users: {CONCURRENT_USERS}")
    print(f"  - Total Events: {TOTAL_EVENTS}")
    print(f"  - Events per User: {EVENTS_PER_USER}")
    print(f"  - Target p95 Latency: < 300ms")

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Server not responding at http://localhost:8000")
            return None
    except Exception as e:
        print(f"\n❌ Cannot connect to server: {e}")
        return None

    print("   ✅ Server is healthy\n")

    # Initialize environments
    user_configs = initialize_environments()

    if len(user_configs) < CONCURRENT_USERS:
        print(f"⚠️  Only initialized {len(user_configs)} environments")
        print(f"   Adjusting concurrent users to {len(user_configs)}")
        actual_users = len(user_configs)
        events_per_user = TOTAL_EVENTS // actual_users
    else:
        actual_users = CONCURRENT_USERS
        events_per_user = EVENTS_PER_USER

    # Create worker threads
    print(f"\n⏱️  Starting load test...")
    print(f"   Creating {actual_users} concurrent threads...")

    threads = []
    start_time = time.time()

    for user_config in user_configs:
        thread = threading.Thread(
            target=create_event_worker,
            args=(user_config["user_id"], user_config, events_per_user),
        )
        threads.append(thread)
        thread.start()

    # Show progress
    last_count = 0
    while any(t.is_alive() for t in threads):
        current_count = metrics.successful_requests + metrics.failed_requests
        if current_count > last_count:
            progress = (current_count / TOTAL_EVENTS) * 100
            print(
                f"   Progress: {current_count}/{TOTAL_EVENTS} requests ({progress:.1f}%)",
                end="\r",
            )
            last_count = current_count
        time.sleep(0.5)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    total_time = time.time() - start_time

    print(f"\n   ✅ Load test completed in {total_time:.2f}s")

    # Get metrics
    summary = metrics.get_summary()
    summary["total_time_seconds"] = round(total_time, 2)
    summary["requests_per_second"] = round(summary["total_requests"] / total_time, 2)
    summary["concurrent_users"] = actual_users
    summary["target_events"] = TOTAL_EVENTS

    # Verify DB consistency
    db_consistent = verify_db_consistency()
    summary["db_consistent"] = db_consistent

    return summary


def print_summary(summary: Dict[str, Any]):
    """Print formatted test summary."""
    print("\n" + "=" * 80)
    print("📊 LOAD TEST RESULTS")
    print("=" * 80)

    print(f"\n⏱️  Timing Metrics:")
    print(f"   Total Time: {summary['total_time_seconds']}s")
    print(f"   Requests/sec: {summary['requests_per_second']}")
    print(f"   Avg Latency: {summary['avg_latency']:.2f}ms")
    print(f"   P95 Latency: {summary['p95_latency']:.2f}ms", end="")

    if summary["p95_latency"] < 300:
        print(" ✅ (< 300ms target)")
    else:
        print(f" ❌ (exceeds 300ms target by {summary['p95_latency'] - 300:.2f}ms)")

    print(f"   P99 Latency: {summary['p99_latency']:.2f}ms")
    print(f"   Min Latency: {summary['min_latency']:.2f}ms")
    print(f"   Max Latency: {summary['max_latency']:.2f}ms")

    print(f"\n📈 Request Metrics:")
    print(f"   Total Requests: {summary['total_requests']}")
    print(
        f"   Successful: {summary['successful_requests']} ({summary['successful_requests']/summary['total_requests']*100:.1f}%)"
    )
    print(
        f"   Failed: {summary['failed_requests']} ({summary['failed_requests']/summary['total_requests']*100:.1f}%)"
    )

    print(f"\n💾 Database Metrics:")
    print(f"   Events Created: {summary['events_created']}")
    print(f"   Unique Events: {summary['unique_events']}")
    print(
        f"   DB Consistency: {'✅ Verified' if summary['db_consistent'] else '❌ Mismatch'}"
    )

    if summary["errors"]:
        print(f"\n❌ Error Breakdown:")
        for error, count in sorted(
            summary["errors"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"   {error}: {count}")

    print("\n" + "=" * 80)
    print("📄 JSON SUMMARY")
    print("=" * 80)

    # Output required JSON
    json_output = {
        "avg_latency": round(summary["avg_latency"], 2),
        "p95_latency": round(summary["p95_latency"], 2),
        "failed_requests": summary["failed_requests"],
    }

    print(json.dumps(json_output, indent=2))

    # Full summary
    print("\n📄 FULL SUMMARY JSON")
    print("=" * 80)
    print(json.dumps(summary, indent=2))

    print("\n" + "=" * 80)


def main():
    """Run the load test."""
    summary = run_load_test()

    if summary:
        print_summary(summary)

        # Save to file
        with open("load_test_results.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n💾 Results saved to: load_test_results.json")
    else:
        print("\n❌ Load test failed to complete")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
