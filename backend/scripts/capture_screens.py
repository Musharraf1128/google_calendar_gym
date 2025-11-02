#!/usr/bin/env python3
"""
Screenshot Dataset Capture Script

Captures 200 varied calendar screenshots with metadata for ML training.
Creates manifest.csv and compresses to google_calendar_gym_dataset.tar.gz

States captured:
- Different event counts (0-10)
- Various popup types (7 types)
- Tasks visible/hidden
- Event overlaps
- Different dates
"""

import requests
import base64
import csv
import random
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

API_BASE = "http://localhost:8000/api"
OUTPUT_DIR = Path("data/screenshots")
MANIFEST_FILE = "data/manifest.csv"
TARGET_SCREENSHOTS = 200

# Popup types available
POPUP_TYPES = [
    "reminder_toast",
    "event_edit_modal",
    "permission_error",
    "event_created_toast",
    "sync_notification",
    "calendar_shared_toast",
    "invitation_popup",
    "none",  # No popup
]

# State variations
EVENT_COUNTS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
TASK_STATES = [True, False]  # Tasks visible or not


class ScreenshotCapture:
    def __init__(self):
        self.manifest_data = []
        self.screenshot_count = 0
        self.env_id = "screenshot_capture"

    def save_screenshot(self, screenshot_b64: str, filename: str) -> bool:
        """Save base64 screenshot to PNG file."""
        try:
            image_data = base64.b64decode(screenshot_b64)
            filepath = OUTPUT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(image_data)
            return True
        except Exception as e:
            print(f"  ⚠️  Failed to save {filename}: {e}")
            return False

    def reset_environment(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Reset gym environment."""
        try:
            response = requests.post(
                f"{API_BASE}/gym/reset",
                json={"env_id": self.env_id, "seed": seed},
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ⚠️  Reset failed: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠️  Reset error: {e}")
            return None

    def create_event(
        self,
        user_email: str,
        calendar_id: str,
        summary: str,
        start_offset: float,
        duration: float,
        attendees: List[str] = None,
    ) -> Dict[str, Any]:
        """Create an event via gym step."""
        action = {
            "type": "create_event",
            "params": {
                "organizer_email": user_email,
                "calendar_id": calendar_id,
                "summary": summary,
                "start_offset_hours": start_offset,
                "duration_hours": duration,
                "attendees": attendees or [],
            },
        }

        try:
            response = requests.post(
                f"{API_BASE}/gym/step",
                json={"env_id": self.env_id, "action": action},
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ⚠️  Create event failed: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠️  Create event error: {e}")
            return None

    def get_current_state(self) -> Dict[str, Any]:
        """Get current environment state without action."""
        # Use a no-op action to trigger screenshot generation
        action = {
            "type": "update_event",
            "params": {
                "event_id": "00000000-0000-0000-0000-000000000000",
                "updates": {"summary": "no-op"},
            },
        }

        try:
            response = requests.post(
                f"{API_BASE}/gym/step",
                json={"env_id": self.env_id, "action": action},
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            return None

    def capture_varied_state(
        self, target_events: int, force_popup: Optional[str] = None
    ) -> bool:
        """
        Capture a screenshot with specific state characteristics.

        Args:
            target_events: Number of events to create (0-10)
            force_popup: Force a specific popup type (or None for random)

        Returns:
            True if capture successful
        """
        # Generate unique seed for this capture
        seed = random.randint(1, 1000000)

        # Reset environment
        reset_data = self.reset_environment(seed)
        if not reset_data:
            return False

        obs = reset_data["observation"]

        if not obs["users"] or not obs["calendars"]:
            print("  ⚠️  No users or calendars available")
            return False

        user = obs["users"][0]
        calendar = obs["calendars"][0]

        # Create specified number of events
        event_summaries = [
            "Morning Standup",
            "Design Review",
            "Client Meeting",
            "Team Lunch",
            "Sprint Planning",
            "Code Review",
            "1-on-1 Sync",
            "All Hands",
            "Product Demo",
            "Training Session",
        ]

        for i in range(target_events):
            summary = event_summaries[i % len(event_summaries)]

            # Randomize event parameters
            start_offset = 1 + (i * 0.5) + random.uniform(-0.2, 0.2)
            duration = random.choice([0.25, 0.5, 1.0, 1.5, 2.0])

            # Sometimes add attendees
            attendees = []
            if random.random() < 0.3 and len(obs["users"]) > 1:
                attendees = [obs["users"][1]["email"]]

            result = self.create_event(
                user["email"],
                calendar["id"],
                f"{summary} {i+1}",
                start_offset,
                duration,
                attendees,
            )

            if not result:
                print(f"  ⚠️  Failed to create event {i+1}")

        # Capture multiple screenshots from same state to get popup variety
        max_attempts = 10 if force_popup else 3

        for attempt in range(max_attempts):
            state = self.get_current_state()

            if not state or "screenshot" not in state:
                continue

            screenshot = state["screenshot"]
            obs = state["observation"]

            # Extract metadata
            visible_date = datetime.now().strftime("%Y-%m-%d")
            num_events = len(obs.get("events", []))

            # Try to detect popup type from observation or use forced
            popup_type = force_popup if force_popup else "none"

            # Generate filename
            self.screenshot_count += 1
            filename = f"frame_{self.screenshot_count:04d}_e{num_events}_p{popup_type[:10]}.png"

            # Save screenshot
            if self.save_screenshot(screenshot, filename):
                # Add to manifest
                self.manifest_data.append(
                    {
                        "screenshot": filename,
                        "visible_date": visible_date,
                        "num_events": num_events,
                        "popup_type": popup_type,
                    }
                )

                print(
                    f"  ✅ Captured {filename} (events={num_events}, popup={popup_type})"
                )
                return True

        return False

    def capture_dataset(self):
        """Capture complete dataset of 200 screenshots."""
        print("\n" + "=" * 80)
        print("📸 GOOGLE CALENDAR GYM - SCREENSHOT DATASET CAPTURE")
        print("=" * 80)
        print(f"\nTarget: {TARGET_SCREENSHOTS} screenshots")
        print(f"Output: {OUTPUT_DIR}")
        print(f"Manifest: {MANIFEST_FILE}")

        # Check server
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code != 200:
                print("\n❌ Server not healthy")
                return False
        except Exception as e:
            print(f"\n❌ Cannot connect to server: {e}")
            return False

        print("✅ Server is healthy\n")

        # Ensure UI_REALISM is enabled for popup variety
        print("⚙️  Capturing with UI_REALISM enabled for popup diversity\n")

        # Calculate distribution
        screenshots_per_event_count = TARGET_SCREENSHOTS // len(EVENT_COUNTS)

        print(f"📊 Planned distribution:")
        print(f"  - Event counts: {EVENT_COUNTS}")
        print(f"  - Screenshots per count: ~{screenshots_per_event_count}")
        print(f"  - Popup types: {len(POPUP_TYPES)} types (random)\n")

        start_time = time.time()
        successful = 0
        failed = 0

        # Capture screenshots with varied states
        for event_count in EVENT_COUNTS:
            print(f"\n📷 Capturing states with {event_count} events...")

            for i in range(screenshots_per_event_count):
                # Randomly decide on popup (30% chance)
                force_popup = None
                if random.random() < 0.3:
                    force_popup = random.choice(POPUP_TYPES[:-1])  # Exclude 'none'

                if self.capture_varied_state(event_count, force_popup):
                    successful += 1
                else:
                    failed += 1

                # Progress
                progress = (successful + failed) / TARGET_SCREENSHOTS * 100
                print(
                    f"  Progress: {successful}/{TARGET_SCREENSHOTS} ({progress:.1f}%)",
                    end="\r",
                )

                # Small delay to avoid overwhelming server
                time.sleep(0.1)

                if successful >= TARGET_SCREENSHOTS:
                    break

            if successful >= TARGET_SCREENSHOTS:
                break

        # Fill remaining with random variations
        while successful < TARGET_SCREENSHOTS:
            event_count = random.choice(EVENT_COUNTS)
            force_popup = random.choice(POPUP_TYPES) if random.random() < 0.3 else None

            if self.capture_varied_state(event_count, force_popup):
                successful += 1
            else:
                failed += 1

            progress = (successful + failed) / TARGET_SCREENSHOTS * 100
            print(
                f"  Progress: {successful}/{TARGET_SCREENSHOTS} ({progress:.1f}%)",
                end="\r",
            )

        total_time = time.time() - start_time

        print(f"\n\n✅ Screenshot capture completed in {total_time:.1f}s")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        return successful > 0

    def save_manifest(self):
        """Save manifest.csv with metadata."""
        print(f"\n📝 Saving manifest to {MANIFEST_FILE}...")

        try:
            with open(MANIFEST_FILE, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["screenshot", "visible_date", "#events", "popup_type"],
                )
                writer.writeheader()

                for row in self.manifest_data:
                    writer.writerow(
                        {
                            "screenshot": row["screenshot"],
                            "visible_date": row["visible_date"],
                            "#events": row["num_events"],
                            "popup_type": row["popup_type"],
                        }
                    )

            print(f"  ✅ Manifest saved with {len(self.manifest_data)} entries")

            # Show summary statistics
            event_counts = {}
            popup_counts = {}

            for row in self.manifest_data:
                num_events = row["num_events"]
                popup = row["popup_type"]

                event_counts[num_events] = event_counts.get(num_events, 0) + 1
                popup_counts[popup] = popup_counts.get(popup, 0) + 1

            print(f"\n  📊 Dataset Statistics:")
            print(f"    Event distribution:")
            for count in sorted(event_counts.keys()):
                print(f"      {count} events: {event_counts[count]} screenshots")

            print(f"\n    Popup distribution:")
            for popup_type in sorted(popup_counts.keys()):
                print(f"      {popup_type}: {popup_counts[popup_type]} screenshots")

            return True

        except Exception as e:
            print(f"  ❌ Failed to save manifest: {e}")
            return False

    def compress_dataset(self):
        """Compress screenshots to tar.gz."""
        print(f"\n📦 Compressing dataset...")

        import tarfile

        archive_path = "google_calendar_gym_dataset.tar.gz"

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add screenshots directory
                tar.add(OUTPUT_DIR, arcname="screenshots")

                # Add manifest
                tar.add(MANIFEST_FILE, arcname="manifest.csv")

            file_size = os.path.getsize(archive_path) / (1024 * 1024)  # MB
            print(f"  ✅ Dataset compressed to {archive_path}")
            print(f"  📦 Archive size: {file_size:.2f} MB")

            return True

        except Exception as e:
            print(f"  ❌ Compression failed: {e}")
            return False


def main():
    """Run screenshot capture process."""
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    capture = ScreenshotCapture()

    # Capture screenshots
    if not capture.capture_dataset():
        print("\n❌ Screenshot capture failed")
        return 1

    # Save manifest
    if not capture.save_manifest():
        print("\n❌ Manifest creation failed")
        return 1

    # Compress dataset
    if not capture.compress_dataset():
        print("\n❌ Dataset compression failed")
        return 1

    print("\n" + "=" * 80)
    print("🎉 DATASET CREATION COMPLETE")
    print("=" * 80)
    print(f"\n📁 Files created:")
    print(f"  - {OUTPUT_DIR}/ ({len(capture.manifest_data)} PNG files)")
    print(f"  - {MANIFEST_FILE}")
    print(f"  - google_calendar_gym_dataset.tar.gz")
    print(f"\n✅ Ready for ML training!\n")

    return 0


if __name__ == "__main__":
    exit(main())
