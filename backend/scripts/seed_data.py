#!/usr/bin/env python3
"""
Comprehensive seed data script for Google Calendar Gym.

Generates:
- 10 users
- 6 calendars (personal + shared)
- ~200 events (single, recurring, cancelled, all-day, timezone-shifted, overlapping)
- Reminders and notifications
- 3+ shared calendars with ACL variety
- Detailed summary statistics
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from uuid import uuid4
from random import randint, choice, random, sample
from app.db import SessionLocal, engine, Base
from app.models.models import (
    User,
    Calendar,
    Event,
    EventAttendee,
    CalendarACL,
    CalendarListEntry,
    Reminder,
    CalendarRole,
    EventStatus,
    AttendeeResponseStatus,
    ReminderMethod,
)

# Create all tables
Base.metadata.create_all(bind=engine)


def clear_database(db):
    """Clear all data from database."""
    print("🗑️  Clearing existing data...")
    db.query(Reminder).delete()
    db.query(EventAttendee).delete()
    db.query(Event).delete()
    db.query(CalendarACL).delete()
    db.query(CalendarListEntry).delete()
    db.query(Calendar).delete()
    db.query(User).delete()
    db.commit()


def create_users(db):
    """Create 10 users."""
    print("\n👥 Creating 10 users...")

    users_data = [
        {"email": "alice@example.com", "name": "Alice Johnson"},
        {"email": "bob@example.com", "name": "Bob Smith"},
        {"email": "charlie@example.com", "name": "Charlie Davis"},
        {"email": "diana@example.com", "name": "Diana Martinez"},
        {"email": "ethan@example.com", "name": "Ethan Brown"},
        {"email": "fiona@example.com", "name": "Fiona Wilson"},
        {"email": "george@example.com", "name": "George Taylor"},
        {"email": "hannah@example.com", "name": "Hannah Anderson"},
        {"email": "ian@example.com", "name": "Ian Thomas"},
        {"email": "julia@example.com", "name": "Julia Lee"},
    ]

    users = {}
    for user_data in users_data:
        user = User(id=uuid4(), email=user_data["email"], name=user_data["name"])
        db.add(user)
        users[user_data["email"]] = user
        print(f"   ✓ Created user: {user.name} ({user.email})")

    db.commit()

    # Refresh to get IDs
    for user in users.values():
        db.refresh(user)

    return users


def create_calendars(db, users):
    """Create 6 calendars (personal + shared)."""
    print("\n📅 Creating 6 calendars...")

    calendars = {}
    user_emails = list(users.keys())

    # Create 3 personal calendars
    for i, email in enumerate(user_emails[:3]):
        user = users[email]
        calendar = Calendar(
            id=uuid4(),
            title=f"{user.name}'s Calendar",
            timezone="America/New_York",
            owner_id=user.id,
            description=f"Personal calendar for {user.name}",
        )
        db.add(calendar)
        db.flush()

        # Create calendar list entry
        entry = CalendarListEntry(
            user_id=user.id,
            calendar_id=calendar.id,
            is_primary=True,
            default_reminders=[
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60},
            ],
        )
        db.add(entry)

        calendars[f"personal_{i+1}"] = calendar
        print(f"   ✓ Created calendar: {calendar.title}")

    # Create 3 shared calendars with different purposes
    shared_calendars_data = [
        {
            "title": "Engineering Team",
            "description": "Shared calendar for engineering team",
            "owner": user_emails[0],
        },
        {
            "title": "Marketing Team",
            "description": "Shared calendar for marketing team",
            "owner": user_emails[1],
        },
        {
            "title": "Company Events",
            "description": "Company-wide events and holidays",
            "owner": user_emails[2],
        },
    ]

    for i, cal_data in enumerate(shared_calendars_data):
        owner = users[cal_data["owner"]]
        calendar = Calendar(
            id=uuid4(),
            title=cal_data["title"],
            timezone="America/New_York",
            owner_id=owner.id,
            description=cal_data["description"],
        )
        db.add(calendar)
        db.flush()

        calendars[f"shared_{i+1}"] = calendar
        print(f"   ✓ Created shared calendar: {calendar.title}")

    db.commit()

    # Refresh calendars
    for calendar in calendars.values():
        db.refresh(calendar)

    return calendars


def create_acl_entries(db, users, calendars):
    """Create ACL entries for shared calendars with variety."""
    print("\n🔐 Creating ACL entries with CalendarListEntry records...")

    acl_count = 0
    user_emails = list(users.keys())

    # Engineering Team - Various roles
    eng_calendar = calendars["shared_1"]
    eng_acls = [
        (user_emails[1], CalendarRole.WRITER),
        (user_emails[2], CalendarRole.WRITER),
        (user_emails[3], CalendarRole.READER),
        (user_emails[4], CalendarRole.READER),
        (user_emails[5], CalendarRole.FREE_BUSY_READER),
    ]

    for email, role in eng_acls:
        acl = CalendarACL(calendar_id=eng_calendar.id, grantee=email, role=role)
        db.add(acl)

        # Also create CalendarListEntry so user can see this calendar
        user = users[email]
        cal_list_entry = CalendarListEntry(
            user_id=user.id,
            calendar_id=eng_calendar.id,
            is_primary=False
        )
        db.add(cal_list_entry)

        acl_count += 1
        print(f"   ✓ Granted {role.value} to {email} on {eng_calendar.title}")

    # Marketing Team - Different mix
    mkt_calendar = calendars["shared_2"]
    mkt_acls = [
        (user_emails[0], CalendarRole.READER),
        (user_emails[3], CalendarRole.WRITER),
        (user_emails[4], CalendarRole.WRITER),
        (user_emails[6], CalendarRole.READER),
    ]

    for email, role in mkt_acls:
        acl = CalendarACL(calendar_id=mkt_calendar.id, grantee=email, role=role)
        db.add(acl)

        # Also create CalendarListEntry so user can see this calendar
        user = users[email]
        cal_list_entry = CalendarListEntry(
            user_id=user.id,
            calendar_id=mkt_calendar.id,
            is_primary=False
        )
        db.add(cal_list_entry)

        acl_count += 1
        print(f"   ✓ Granted {role.value} to {email} on {mkt_calendar.title}")

    # Company Events - Wide access
    company_calendar = calendars["shared_3"]
    for email in user_emails:
        if email != user_emails[2]:  # Skip owner
            role = CalendarRole.READER if random() > 0.3 else CalendarRole.WRITER
            acl = CalendarACL(calendar_id=company_calendar.id, grantee=email, role=role)
            db.add(acl)

            # Also create CalendarListEntry so user can see this calendar
            user = users[email]
            cal_list_entry = CalendarListEntry(
                user_id=user.id,
                calendar_id=company_calendar.id,
                is_primary=False
            )
            db.add(cal_list_entry)

            acl_count += 1
            print(
                f"   ✓ Granted {role.value} to {email} on {company_calendar.title}"
            )

    db.commit()
    return acl_count


def create_comprehensive_events(db, users, calendars):
    """Create ~200 events with variety."""
    print("\n📌 Creating ~200 diverse events...")

    events_created = 0
    now = datetime.now()
    user_emails = list(users.keys())

    # Event templates for variety
    event_types = []

    # 1. Single events (80 events)
    print("\n   Creating single events...")
    for i in range(80):
        calendar_key = choice(list(calendars.keys()))
        calendar = calendars[calendar_key]

        # Random time in next 60 days
        days_offset = randint(-30, 30)
        hour = randint(8, 18)
        minute = choice([0, 15, 30, 45])

        start = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(
            days=days_offset
        )
        duration = choice([30, 60, 90, 120, 180])  # minutes
        end = start + timedelta(minutes=duration)

        # Random status (90% confirmed, 5% tentative, 5% cancelled)
        status_rand = random()
        if status_rand < 0.90:
            status = EventStatus.CONFIRMED
        elif status_rand < 0.95:
            status = EventStatus.TENTATIVE
        else:
            status = EventStatus.CANCELLED

        # Random color
        color_id = randint(0, 7)

        event = Event(
            id=uuid4(),
            calendar_id=calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary=choice(
                [
                    "Team Meeting",
                    "Client Call",
                    "Project Review",
                    "Design Review",
                    "Code Review",
                    "Sprint Planning",
                    "Retrospective",
                    "1:1 Meeting",
                    "Lunch Break",
                    "Training Session",
                    "Workshop",
                    "Demo Day",
                ]
            ),
            description=f"Event {i+1} - Status: {status.value}",
            start=start,
            end=end,
            location=choice(
                [
                    "Conference Room A",
                    "Conference Room B",
                    "Zoom",
                    "Office",
                    None,
                    "Building 2",
                    "Remote",
                ]
            ),
            status=status,
            is_all_day=False,
            color_id=color_id,
        )
        db.add(event)
        db.flush()

        # Add reminders (70% chance)
        if random() < 0.7:
            # Add 1-2 reminders
            num_reminders = 1 if random() < 0.6 else 2
            for _ in range(num_reminders):
                reminder = Reminder(
                    event_id=event.id,
                    method=choice([ReminderMethod.POPUP, ReminderMethod.EMAIL]),
                    minutes_before=choice([10, 15, 30, 60, 1440]),  # 1440 = 1 day
                )
                db.add(reminder)

        # Add attendees (50% chance)
        if random() < 0.5:
            num_attendees = randint(1, 4)
            attendee_emails = sample(user_emails, min(num_attendees, len(user_emails)))

            for attendee_email in attendee_emails:
                attendee = EventAttendee(
                    event_id=event.id,
                    email=attendee_email,
                    display_name=users[attendee_email].name,
                    response_status=choice(
                        [
                            AttendeeResponseStatus.ACCEPTED,
                            AttendeeResponseStatus.NEEDS_ACTION,
                            AttendeeResponseStatus.TENTATIVE,
                            AttendeeResponseStatus.DECLINED,
                        ]
                    ),
                    is_organizer=(attendee_email == user_emails[0]),
                    is_optional=random() < 0.3,
                )
                db.add(attendee)

        events_created += 1

        if events_created % 20 == 0:
            print(f"   ✓ Created {events_created} events...")

    db.commit()

    # 2. All-day events (30 events)
    print("\n   Creating all-day events...")
    for i in range(30):
        calendar_key = choice(list(calendars.keys()))
        calendar = calendars[calendar_key]

        days_offset = randint(-30, 30)
        start = (now + timedelta(days=days_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=1)

        event = Event(
            id=uuid4(),
            calendar_id=calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary=choice(
                [
                    "Company Holiday",
                    "Birthday",
                    "Vacation Day",
                    "Public Holiday",
                    "Conference",
                    "Team Offsite",
                    "Holiday",
                ]
            ),
            description=f"All-day event {i+1}",
            start=start,
            end=end,
            status=EventStatus.CONFIRMED,
            is_all_day=True,
            color_id=randint(0, 7),
        )
        db.add(event)
        events_created += 1

    db.commit()
    print(f"   ✓ Created {events_created} events (including all-day)...")

    # 3. Recurring events (40 events total - will generate ~200 instances)
    print("\n   Creating recurring events...")
    recurring_patterns = [
        {
            "summary": "Daily Standup",
            "recurrence": ["RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR;COUNT=30"],
            "duration": 15,
        },
        {
            "summary": "Weekly Team Sync",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=12"],
            "duration": 60,
        },
        {
            "summary": "Bi-weekly Sprint Planning",
            "recurrence": ["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=WE;COUNT=6"],
            "duration": 120,
        },
        {
            "summary": "Monthly All-Hands",
            "recurrence": ["RRULE:FREQ=MONTHLY;BYDAY=1FR;COUNT=6"],
            "duration": 90,
        },
        {
            "summary": "Quarterly Board Meeting",
            "recurrence": ["RRULE:FREQ=MONTHLY;INTERVAL=3;COUNT=4"],
            "duration": 180,
        },
    ]

    for i in range(40):
        calendar_key = choice(list(calendars.keys()))
        calendar = calendars[calendar_key]

        pattern = choice(recurring_patterns)
        days_offset = randint(0, 14)
        hour = randint(9, 17)

        start = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(
            days=days_offset
        )
        end = start + timedelta(minutes=pattern["duration"])

        event = Event(
            id=uuid4(),
            calendar_id=calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary=pattern["summary"],
            description=f"Recurring event {i+1}",
            start=start,
            end=end,
            recurrence=pattern["recurrence"],
            status=EventStatus.CONFIRMED,
            is_all_day=False,
            color_id=randint(0, 7),
        )
        db.add(event)
        db.flush()

        # Add reminders to recurring events
        reminder = Reminder(
            event_id=event.id, method=ReminderMethod.POPUP, minutes_before=30
        )
        db.add(reminder)

        events_created += 1

    db.commit()
    print(f"   ✓ Created {events_created} total events (including recurring)...")

    # 4. Overlapping events (20 events)
    print("\n   Creating overlapping events...")
    for i in range(20):
        # Pick a random existing event to overlap with
        existing_events = db.query(Event).filter(Event.is_all_day == False).limit(50).all()
        if existing_events:
            base_event = choice(existing_events)

            # Create overlapping event
            overlap_start = base_event.start + timedelta(minutes=15)
            overlap_end = base_event.end - timedelta(minutes=15)

            if overlap_end > overlap_start:
                event = Event(
                    id=uuid4(),
                    calendar_id=base_event.calendar_id,
                    iCalUID=f"{uuid4()}@calendar.app",
                    summary="Overlapping Meeting",
                    description=f"Overlaps with {base_event.summary}",
                    start=overlap_start,
                    end=overlap_end,
                    status=EventStatus.TENTATIVE,
                    is_all_day=False,
                    color_id=randint(0, 7),
                )
                db.add(event)
                events_created += 1

    db.commit()
    print(f"   ✓ Created {events_created} total events...")

    # 5. Timezone-shifted events (10 events)
    print("\n   Creating timezone-shifted events...")
    for i in range(10):
        calendar_key = choice(list(calendars.keys()))
        calendar = calendars[calendar_key]

        # Create event at unusual times (simulating timezone differences)
        hour = choice([1, 2, 3, 22, 23])  # Late night / early morning
        minute = choice([0, 30])

        start = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(
            days=randint(0, 30)
        )
        end = start + timedelta(hours=1)

        event = Event(
            id=uuid4(),
            calendar_id=calendar.id,
            iCalUID=f"{uuid4()}@calendar.app",
            summary=choice(["International Call", "APAC Meeting", "Europe Sync"]),
            description=f"Timezone-shifted event {i+1}",
            start=start,
            end=end,
            location="Zoom",
            status=EventStatus.CONFIRMED,
            is_all_day=False,
            color_id=randint(0, 7),
        )
        db.add(event)
        events_created += 1

    db.commit()
    print(f"\n   ✅ Total events created: {events_created}")

    return events_created


def print_comprehensive_summary(db):
    """Print detailed summary statistics."""
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE SEED DATA SUMMARY")
    print("=" * 70)

    # Basic counts
    user_count = db.query(User).count()
    calendar_count = db.query(Calendar).count()
    event_count = db.query(Event).count()
    attendee_count = db.query(EventAttendee).count()
    acl_count = db.query(CalendarACL).count()
    reminder_count = db.query(Reminder).count()

    print(f"\n👥 Users:                    {user_count}")
    print(f"📅 Calendars:                {calendar_count}")
    print(f"   - Personal:               {calendar_count - 3}")
    print(f"   - Shared:                 3")
    print(f"\n📌 Total Events:             {event_count}")

    # Event type breakdown
    single_count = (
        db.query(Event)
        .filter(Event.recurrence.is_(None), Event.is_all_day == False)
        .count()
    )
    recurring_count = db.query(Event).filter(Event.recurrence.isnot(None)).count()
    all_day_count = db.query(Event).filter(Event.is_all_day == True).count()

    print(f"   - Single events:          {single_count}")
    print(f"   - Recurring events:       {recurring_count}")
    print(f"   - All-day events:         {all_day_count}")

    # Status breakdown
    confirmed_count = db.query(Event).filter(Event.status == EventStatus.CONFIRMED).count()
    tentative_count = db.query(Event).filter(Event.status == EventStatus.TENTATIVE).count()
    cancelled_count = db.query(Event).filter(Event.status == EventStatus.CANCELLED).count()

    print(f"\n   By Status:")
    print(f"   - Confirmed:              {confirmed_count}")
    print(f"   - Tentative:              {tentative_count}")
    print(f"   - Cancelled:              {cancelled_count}")

    # Attendees and reminders
    print(f"\n👤 Event Attendees:          {attendee_count}")
    print(f"🔔 Reminders:                {reminder_count}")
    print(f"🔐 ACL Entries:              {acl_count}")

    # ACL breakdown by role
    owner_acl = db.query(CalendarACL).filter(CalendarACL.role == CalendarRole.OWNER).count()
    writer_acl = db.query(CalendarACL).filter(CalendarACL.role == CalendarRole.WRITER).count()
    reader_acl = db.query(CalendarACL).filter(CalendarACL.role == CalendarRole.READER).count()
    freebusy_acl = (
        db.query(CalendarACL).filter(CalendarACL.role == CalendarRole.FREE_BUSY_READER).count()
    )

    print(f"\n   ACL by Role:")
    print(f"   - Owner:                  {owner_acl}")
    print(f"   - Writer:                 {writer_acl}")
    print(f"   - Reader:                 {reader_acl}")
    print(f"   - FreeBusy Reader:        {freebusy_acl}")

    print("\n" + "=" * 70)
    print("✅ Database seeded successfully with comprehensive test data!")
    print("=" * 70)

    # Print 5 sample events
    print("\n🔍 SAMPLE 5 EVENTS:")
    print("-" * 70)

    sample_events = db.query(Event).limit(5).all()

    for i, event in enumerate(sample_events, 1):
        calendar = db.query(Calendar).filter(Calendar.id == event.calendar_id).first()
        attendees = (
            db.query(EventAttendee).filter(EventAttendee.event_id == event.id).count()
        )
        reminders = db.query(Reminder).filter(Reminder.event_id == event.id).count()

        print(f"\n{i}. {event.summary}")
        print(f"   Calendar:     {calendar.title}")
        print(f"   Start:        {event.start.strftime('%Y-%m-%d %H:%M')}")
        print(f"   End:          {event.end.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Status:       {event.status.value}")
        print(f"   All-day:      {event.is_all_day}")
        print(f"   Recurring:    {'Yes' if event.recurrence else 'No'}")
        print(f"   Color:        {event.color_id}")
        print(f"   Attendees:    {attendees}")
        print(f"   Reminders:    {reminders}")
        if event.location:
            print(f"   Location:     {event.location}")

    print("\n" + "=" * 70)


def main():
    """Main seeding function."""
    print("=" * 70)
    print("🌱 SEEDING DATABASE WITH COMPREHENSIVE TEST DATA")
    print("=" * 70)

    db = SessionLocal()

    try:
        # Clear existing data
        clear_database(db)

        # Create data
        users = create_users(db)
        calendars = create_calendars(db, users)
        acl_count = create_acl_entries(db, users, calendars)
        event_count = create_comprehensive_events(db, users, calendars)

        # Print comprehensive summary
        print_comprehensive_summary(db)

        print("\n🎉 You can now:")
        print("   1. Start the backend: uvicorn app.main:app --reload --port 8000")
        print("   2. Start the frontend: cd frontend && npm run dev")
        print("   3. Visit http://localhost:5173")
        print("   4. Select any user from the 10 available users")
        print("\n💡 Tips:")
        print(
            "   - Try different users to see shared calendars with different permissions"
        )
        print("   - Look for overlapping events, all-day events, and cancelled events")
        print("   - Check reminders and attendee responses")
        print("   - Explore recurring events across multiple weeks")

    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
