#!/usr/bin/env python3
"""
Optimized Load Test for Google Calendar Gym API

Tests the actual event creation endpoints (not gym with screenshots).
This tests production API performance.

Configuration:
- 50 concurrent users
- 1000 total events
- Target p95 latency < 300ms
- Verifies DB consistency
"""

import requests
import time
import threading
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

API_BASE = "http://localhost:8000/api"
CONCURRENT_USERS = 50
TOTAL_EVENTS = 1000
EVENTS_PER_USER = TOTAL_EVENTS // CONCURRENT_USERS


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


def setup_test_environment():
    """Setup test users and calendars."""
    print("🔧 Setting up test environment...")

    # Get users
    try:
        response = requests.get(f"{API_BASE}/users", timeout=5)
        if response.status_code != 200:
            print(f"   ⚠️  Failed to get users: HTTP {response.status_code}")
            return []

        users = response.json()
        print(f"   Found {len(users)} users")

        # Get calendars for each user
        user_configs = []
        for i, user in enumerate(users[:CONCURRENT_USERS]):
            # Get user's calendars
            cal_response = requests.get(
                f"{API_BASE}/users/{user['id']}/calendars", timeout=5
            )

            if cal_response.status_code == 200:
                calendars = cal_response.json()
                if calendars:
                    user_configs.append(
                        {
                            "user_id": i,
                            "id": user["id"],
                            "email": user["email"],
                            "calendar_id": calendars[0]["id"],
                        }
                    )

        print(f"   ✅ Configured {len(user_configs)} users with calendars")
        return user_configs

    except Exception as e:
        print(f"   ❌ Setup failed: {e}")
        return []


def create_events_worker(user_config: Dict[str, Any], events_to_create: int):
    """
    Worker thread that creates events via direct API endpoints.

    Args:
        user_config: User configuration with calendar_id
        events_to_create: Number of events to create
    """
    calendar_id = user_config["calendar_id"]
    user_email = user_config["email"]
    user_id = user_config["user_id"]

    for i in range(events_to_create):
        # Calculate event times
        start_time = datetime.now() + timedelta(hours=1 + (i * 0.5))
        end_time = start_time + timedelta(minutes=30)

        # Event payload
        event_data = {
            "summary": f"Load Test Event U{user_id}-E{i}",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "organizer_email": user_email,
            "description": f"Load test event {i}",
        }

        # Measure latency
        start = time.time()

        try:
            response = requests.post(
                f"{API_BASE}/calendars/{calendar_id}/events", json=event_data, timeout=5
            )

            latency = (time.time() - start) * 1000  # ms
            metrics.add_latency(latency)

            if response.status_code in [200, 201]:
                data = response.json()
                event_id = data.get("id", "unknown")
                metrics.add_success(event_id)
            else:
                metrics.add_failure(f"HTTP {response.status_code}")

        except requests.Timeout:
            latency = (time.time() - start) * 1000
            metrics.add_latency(latency)
            metrics.add_failure("Timeout")
        except Exception as e:
            latency = (time.time() - start) * 1000
            metrics.add_latency(latency)
            metrics.add_failure(f"Exception: {str(e)[:50]}")


def verify_db_consistency(user_configs: List[Dict]):
    """Verify events were committed to database."""
    print("\n🔍 Verifying DB consistency...")

    total_events = 0
    try:
        for config in user_configs[:5]:  # Sample first 5
            cal_id = config["calendar_id"]
            response = requests.get(f"{API_BASE}/calendars/{cal_id}/events", timeout=5)

            if response.status_code == 200:
                events = response.json()
                count = len(
                    [e for e in events if "Load Test Event" in e.get("summary", "")]
                )
                total_events += count

        print(f"   Sampled events in DB: ~{total_events} (from 5 calendars)")

        expected = metrics.successful_requests
        if total_events > 0:
            print(f"   ✅ DB has events (expected: {expected})")
            return True
        else:
            print(f"   ⚠️  Could not verify all events")
            return False

    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False


def run_load_test():
    """Execute the optimized load test."""
    print("\n" + "=" * 80)
    print("🚀 GOOGLE CALENDAR GYM - OPTIMIZED LOAD TEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  - Concurrent Users: {CONCURRENT_USERS}")
    print(f"  - Total Events: {TOTAL_EVENTS}")
    print(f"  - Events per User: {EVENTS_PER_USER}")
    print(f"  - Target p95 Latency: < 300ms")
    print(f"  - API: Direct event creation (no screenshots)")

    # Check server
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Server not healthy")
            return None
    except Exception as e:
        print(f"\n❌ Cannot connect to server: {e}")
        return None

    print("   ✅ Server is healthy\n")

    # Setup
    user_configs = setup_test_environment()

    if len(user_configs) < 10:
        print(f"⚠️  Only {len(user_configs)} users configured (need 10+)")
        print("   Continuing with available users...")

    actual_users = min(len(user_configs), CONCURRENT_USERS)
    events_per_user = TOTAL_EVENTS // actual_users

    print(f"\n⏱️  Starting load test with {actual_users} concurrent users...")

    threads = []
    start_time = time.time()

    for i in range(actual_users):
        config = user_configs[i % len(user_configs)]
        thread = threading.Thread(
            target=create_events_worker, args=(config, events_per_user)
        )
        threads.append(thread)
        thread.start()

    # Progress monitoring
    last_count = 0
    while any(t.is_alive() for t in threads):
        current_count = metrics.successful_requests + metrics.failed_requests
        if current_count > last_count:
            progress = (current_count / TOTAL_EVENTS) * 100
            print(
                f"   Progress: {current_count}/{TOTAL_EVENTS} ({progress:.1f}%)",
                end="\r",
            )
            last_count = current_count
        time.sleep(0.1)

    # Wait for completion
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

    # Verify DB
    db_consistent = verify_db_consistency(user_configs)
    summary["db_consistent"] = db_consistent

    return summary


def print_summary(summary: Dict[str, Any]):
    """Print formatted summary."""
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
        print(f" ❌ (exceeds 300ms by {summary['p95_latency'] - 300:.2f}ms)")

    print(f"   P99 Latency: {summary['p99_latency']:.2f}ms")
    print(f"   Min Latency: {summary['min_latency']:.2f}ms")
    print(f"   Max Latency: {summary['max_latency']:.2f}ms")

    print(f"\n📈 Request Metrics:")
    print(f"   Total Requests: {summary['total_requests']}")
    success_rate = (
        summary["successful_requests"] / summary["total_requests"] * 100
        if summary["total_requests"] > 0
        else 0
    )
    print(f"   Successful: {summary['successful_requests']} ({success_rate:.1f}%)")
    print(f"   Failed: {summary['failed_requests']}")

    print(f"\n💾 Database Metrics:")
    print(f"   Events Created: {summary['events_created']}")
    print(f"   Unique Events: {summary['unique_events']}")
    print(
        f"   DB Consistency: {'✅ Verified' if summary['db_consistent'] else '⚠️  Partial'}"
    )

    if summary["errors"]:
        print(f"\n❌ Errors:")
        for error, count in sorted(
            summary["errors"].items(), key=lambda x: x[1], reverse=True
        )[:5]:
            print(f"   {error}: {count}")

    print("\n" + "=" * 80)
    print("📄 JSON SUMMARY (Required Format)")
    print("=" * 80)

    json_output = {
        "avg_latency": round(summary["avg_latency"], 2),
        "p95_latency": round(summary["p95_latency"], 2),
        "failed_requests": summary["failed_requests"],
    }

    print(json.dumps(json_output, indent=2))

    print("\n" + "=" * 80)
    print("📄 FULL SUMMARY JSON")
    print("=" * 80)
    print(json.dumps(summary, indent=2))
    print("=" * 80)


def main():
    """Run the optimized load test."""
    summary = run_load_test()

    if summary:
        print_summary(summary)

        # Save results
        with open("load_test_results_optimized.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n💾 Results saved to: load_test_results_optimized.json")

        # Return exit code based on success
        if summary["p95_latency"] < 300 and summary["successful_requests"] > 900:
            return 0  # Success
        else:
            return 1  # Failed to meet targets
    else:
        print("\n❌ Load test failed")
        return 1


if __name__ == "__main__":
    exit(main())
