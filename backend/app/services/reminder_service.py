"""
Reminder Service using APScheduler for event notifications.

This service:
- Schedules reminders for calendar events
- Supports default reminders from CalendarListEntry
- Supports event-level reminder overrides
- Logs notifications to NotificationLog table
- Handles reminder rescheduling when events are updated
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session

from app.models.models import (
    Event,
    Reminder,
    ReminderMethod,
    NotificationLog,
    CalendarListEntry,
)
from app.db import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None

# Global session factory (can be overridden for testing)
_session_factory = SessionLocal


def get_scheduler() -> BackgroundScheduler:
    """
    Get or create the global APScheduler instance.

    Returns:
        BackgroundScheduler instance
    """
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("APScheduler started")
    return scheduler


def stop_scheduler():
    """Stop the global scheduler (useful for testing and shutdown)."""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("APScheduler stopped")


def set_session_factory(factory):
    """
    Set a custom session factory (useful for testing).

    Args:
        factory: A callable that returns a database session
    """
    global _session_factory
    _session_factory = factory


def send_notification(
    event_id: UUID,
    user_id: Optional[UUID],
    reminder_method: ReminderMethod,
    minutes_before: int,
    scheduled_time: datetime,
    event_summary: str,
    event_start: datetime,
):
    """
    Simulate sending a notification by logging it to NotificationLog.

    This function is called by APScheduler at the scheduled time.

    Args:
        event_id: ID of the event
        user_id: ID of the user to notify (optional)
        reminder_method: Method of notification (email, popup)
        minutes_before: How many minutes before event this reminder is for
        scheduled_time: When this reminder was scheduled to fire
        event_summary: Summary of the event
        event_start: Start time of the event
    """
    db = _session_factory()
    try:
        # Create notification message
        time_str = f"{minutes_before} minute{'s' if minutes_before != 1 else ''}"
        message = f"Reminder: '{event_summary}' starts in {time_str} at {event_start.strftime('%Y-%m-%d %H:%M')}"

        # Log the notification
        notification = NotificationLog(
            event_id=event_id,
            user_id=user_id,
            reminder_method=reminder_method,
            minutes_before=minutes_before,
            scheduled_time=scheduled_time,
            event_summary=event_summary,
            event_start=event_start,
            message=message,
        )

        db.add(notification)
        db.commit()

        logger.info(
            f"Notification sent: {reminder_method.value} for event {event_id} "
            f"({minutes_before} min before)"
        )

    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        db.rollback()
    finally:
        db.close()


def get_event_reminders(db: Session, event: Event) -> List[Dict[str, Any]]:
    """
    Get the reminders for an event, considering both event-level and default reminders.

    Priority:
    1. Event-level reminders (if any exist)
    2. Default reminders from CalendarListEntry (if event has no reminders)

    Args:
        db: Database session
        event: Event object

    Returns:
        List of reminder dictionaries with 'method' and 'minutes_before'
    """
    reminders = []

    # Check if event has explicit reminders
    if event.reminders and len(event.reminders) > 0:
        # Use event-level reminders
        for reminder in event.reminders:
            reminders.append(
                {"method": reminder.method, "minutes_before": reminder.minutes_before}
            )
    else:
        # Fall back to default reminders from calendar list entry
        # Find the calendar list entry for the event's calendar owner
        calendar = event.calendar
        if calendar:
            entry = (
                db.query(CalendarListEntry)
                .filter(
                    CalendarListEntry.calendar_id == calendar.id,
                    CalendarListEntry.user_id == calendar.owner_id,
                )
                .first()
            )

            if entry and entry.default_reminders:
                # default_reminders is a JSON array like [{"method": "popup", "minutes": 30}]
                for default_reminder in entry.default_reminders:
                    method_str = default_reminder.get("method", "popup")
                    # Convert string to ReminderMethod enum
                    method = (
                        ReminderMethod(method_str)
                        if isinstance(method_str, str)
                        else method_str
                    )
                    reminders.append(
                        {
                            "method": method,
                            "minutes_before": default_reminder.get("minutes", 30),
                        }
                    )

    return reminders


def schedule_reminders(db: Session, event: Event, test_mode: bool = False):
    """
    Schedule reminders for an event.

    This function:
    1. Gets reminders for the event (event-level or defaults)
    2. Calculates the notification time for each reminder
    3. Schedules jobs with APScheduler to send notifications
    4. In test mode, uses shorter delays for testing

    Args:
        db: Database session
        event: Event object to schedule reminders for
        test_mode: If True, use seconds instead of minutes for testing

    Example:
        >>> event = db.query(Event).filter(Event.id == event_id).first()
        >>> schedule_reminders(db, event)
    """
    scheduler_instance = get_scheduler()

    # Get reminders for this event
    reminders = get_event_reminders(db, event)

    if not reminders:
        logger.debug(f"No reminders to schedule for event {event.id}")
        return

    now = datetime.now()

    for reminder_config in reminders:
        method = reminder_config["method"]
        minutes_before = reminder_config["minutes_before"]

        # Calculate when to send the reminder
        if test_mode:
            # In test mode, treat "minutes" as seconds for quick testing
            scheduled_time = event.start - timedelta(seconds=minutes_before)
        else:
            scheduled_time = event.start - timedelta(minutes=minutes_before)

        # Only schedule if the reminder time is in the future
        if scheduled_time <= now:
            logger.debug(
                f"Skipping past reminder for event {event.id}: "
                f"scheduled_time={scheduled_time}, now={now}"
            )
            continue

        # Create a unique job ID
        job_id = f"reminder_{event.id}_{method.value}_{minutes_before}"

        # Get the calendar owner (user to notify)
        user_id = event.calendar.owner_id if event.calendar else None

        # Schedule the job
        scheduler_instance.add_job(
            send_notification,
            trigger=DateTrigger(run_date=scheduled_time),
            id=job_id,
            replace_existing=True,  # Replace if already exists
            args=[
                event.id,
                user_id,
                method,
                minutes_before,
                scheduled_time,
                event.summary,
                event.start,
            ],
        )

        logger.info(
            f"Scheduled reminder for event {event.id} ({event.summary}): "
            f"{method.value} {minutes_before} {'seconds' if test_mode else 'minutes'} before at {scheduled_time}"
        )


def cancel_event_reminders(event_id: UUID):
    """
    Cancel all scheduled reminders for an event.

    Args:
        event_id: ID of the event
    """
    scheduler_instance = get_scheduler()

    # Get all jobs that start with the event ID prefix
    jobs = scheduler_instance.get_jobs()
    cancelled_count = 0

    for job in jobs:
        if job.id.startswith(f"reminder_{event_id}_"):
            scheduler_instance.remove_job(job.id)
            cancelled_count += 1
            logger.info(f"Cancelled reminder job: {job.id}")

    if cancelled_count > 0:
        logger.info(f"Cancelled {cancelled_count} reminder(s) for event {event_id}")


def reschedule_reminders(db: Session, event: Event, test_mode: bool = False):
    """
    Reschedule reminders for an event (e.g., after event time changes).

    This cancels existing reminders and creates new ones.

    Args:
        db: Database session
        event: Event object
        test_mode: If True, use seconds instead of minutes for testing
    """
    # Cancel existing reminders
    cancel_event_reminders(event.id)

    # Schedule new reminders
    schedule_reminders(db, event, test_mode=test_mode)


def set_event_reminders(
    db: Session,
    event_id: UUID,
    reminders: List[Dict[str, Any]],
    test_mode: bool = False,
) -> Event:
    """
    Set custom reminders for an event (overrides defaults).

    Args:
        db: Database session
        event_id: ID of the event
        reminders: List of reminder dicts with 'method' and 'minutes_before'
        test_mode: If True, use seconds for testing

    Returns:
        Updated Event object

    Raises:
        ValueError: If event not found

    Example:
        >>> reminders = [
        ...     {"method": "popup", "minutes_before": 30},
        ...     {"method": "email", "minutes_before": 60}
        ... ]
        >>> event = set_event_reminders(db, event_id, reminders)
    """
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise ValueError(f"Event with id {event_id} not found")

    # Delete existing event reminders
    db.query(Reminder).filter(Reminder.event_id == event_id).delete()

    # Add new reminders
    for reminder_data in reminders:
        method_value = reminder_data.get("method")

        # Handle both string and enum values
        if isinstance(method_value, str):
            method = ReminderMethod(method_value)
        else:
            method = method_value

        reminder = Reminder(
            event_id=event_id,
            method=method,
            minutes_before=reminder_data.get("minutes_before"),
        )
        db.add(reminder)

    db.commit()
    db.refresh(event)

    # Reschedule reminders with the new settings
    reschedule_reminders(db, event, test_mode=test_mode)

    return event


def get_notification_logs(
    db: Session,
    event_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    limit: int = 100,
) -> List[NotificationLog]:
    """
    Get notification logs, optionally filtered by event or user.

    Args:
        db: Database session
        event_id: Optional event ID to filter by
        user_id: Optional user ID to filter by
        limit: Maximum number of logs to return

    Returns:
        List of NotificationLog objects
    """
    query = db.query(NotificationLog)

    if event_id:
        query = query.filter(NotificationLog.event_id == event_id)

    if user_id:
        query = query.filter(NotificationLog.user_id == user_id)

    return query.order_by(NotificationLog.sent_time.desc()).limit(limit).all()
