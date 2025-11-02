"""
Recurrence utilities for expanding recurring events using RFC 5545 (iCalendar) format.

This module provides functions to parse and expand recurrence rules (RRULE),
exception dates (EXDATE), and additional dates (RDATE) for calendar events.
"""

from datetime import datetime, timedelta
from typing import List, Set
from dateutil import rrule
from dateutil.parser import parse as parse_date


def parse_rrule_string(rrule_str: str, dtstart: datetime) -> rrule.rrule:
    """
    Parse an RRULE string into a dateutil.rrule.rrule object.

    Args:
        rrule_str: RRULE string in RFC 5545 format (e.g., "FREQ=DAILY;COUNT=10")
        dtstart: Start datetime for the recurrence rule

    Returns:
        rrule.rrule object

    Raises:
        ValueError: If the RRULE string is invalid

    Examples:
        >>> dtstart = datetime(2025, 1, 1, 10, 0)
        >>> rule = parse_rrule_string("FREQ=DAILY;COUNT=5", dtstart)
        >>> rule = parse_rrule_string("FREQ=WEEKLY;BYDAY=TU,FR;COUNT=5", dtstart)
        >>> rule = parse_rrule_string("FREQ=DAILY;INTERVAL=3;UNTIL=20250131T100000Z", dtstart)
    """
    if not rrule_str:
        raise ValueError("RRULE string cannot be empty")

    # Ensure the string starts with RRULE: if not already present
    if not rrule_str.startswith("RRULE:"):
        rrule_str = f"RRULE:{rrule_str}"

    # Add DTSTART to the rule string for proper parsing
    dtstart_str = dtstart.strftime("%Y%m%dT%H%M%S")
    if dtstart.tzinfo:
        dtstart_str += "Z"

    full_rule_str = f"DTSTART:{dtstart_str}\n{rrule_str}"

    try:
        # Parse using rrulestr which handles the full RFC 5545 format
        rule = rrule.rrulestr(full_rule_str, forceset=False)
        return rule
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid RRULE string: {rrule_str}. Error: {str(e)}")


def parse_exdates(exdate_strings: List[str]) -> Set[datetime]:
    """
    Parse EXDATE strings into a set of exception dates.

    Args:
        exdate_strings: List of EXDATE strings (e.g., ["20250115T100000", "20250122T100000"])

    Returns:
        Set of datetime objects representing exception dates

    Examples:
        >>> parse_exdates(["20250115T100000", "20250122T100000"])
        {datetime(2025, 1, 15, 10, 0), datetime(2025, 1, 22, 10, 0)}
    """
    exdates = set()

    for exdate_str in exdate_strings:
        # Remove EXDATE: prefix if present
        if exdate_str.startswith("EXDATE:"):
            exdate_str = exdate_str[7:]

        # Handle multiple dates in one EXDATE line (comma-separated)
        date_parts = exdate_str.split(",")

        for date_part in date_parts:
            date_part = date_part.strip()
            if not date_part:
                continue

            try:
                # Parse datetime string
                if "T" in date_part:
                    # ISO format with time
                    dt = datetime.strptime(date_part.replace("Z", ""), "%Y%m%dT%H%M%S")
                else:
                    # Date only
                    dt = datetime.strptime(date_part, "%Y%m%d")
                exdates.add(dt)
            except ValueError:
                # Try parsing with dateutil as fallback
                try:
                    dt = parse_date(date_part)
                    exdates.add(dt)
                except Exception:
                    # Skip invalid dates
                    continue

    return exdates


def parse_rdates(rdate_strings: List[str]) -> Set[datetime]:
    """
    Parse RDATE strings into a set of additional recurrence dates.

    Args:
        rdate_strings: List of RDATE strings (e.g., ["20250120T100000", "20250127T100000"])

    Returns:
        Set of datetime objects representing additional dates

    Examples:
        >>> parse_rdates(["20250120T100000", "20250127T100000"])
        {datetime(2025, 1, 20, 10, 0), datetime(2025, 1, 27, 10, 0)}
    """
    rdates = set()

    for rdate_str in rdate_strings:
        # Remove RDATE: prefix if present
        if rdate_str.startswith("RDATE:"):
            rdate_str = rdate_str[6:]

        # Handle multiple dates in one RDATE line (comma-separated)
        date_parts = rdate_str.split(",")

        for date_part in date_parts:
            date_part = date_part.strip()
            if not date_part:
                continue

            try:
                # Parse datetime string
                if "T" in date_part:
                    # ISO format with time
                    dt = datetime.strptime(date_part.replace("Z", ""), "%Y%m%dT%H%M%S")
                else:
                    # Date only
                    dt = datetime.strptime(date_part, "%Y%m%d")
                rdates.add(dt)
            except ValueError:
                # Try parsing with dateutil as fallback
                try:
                    dt = parse_date(date_part)
                    rdates.add(dt)
                except Exception:
                    # Skip invalid dates
                    continue

    return rdates


def expand_recurrence(
    event_start: datetime,
    recurrence_field: List[str],
    window_start: datetime,
    window_end: datetime,
    max_instances: int = 1000,
) -> List[datetime]:
    """
    Expand a recurring event into individual occurrences within a time window.

    This function handles:
    - RRULE: Recurrence rules
    - EXDATE: Exception dates (dates to exclude)
    - RDATE: Additional recurrence dates (dates to include)

    Args:
        event_start: The start datetime of the original event
        recurrence_field: List of recurrence strings (RRULE, EXDATE, RDATE lines)
        window_start: Start of the time window to expand occurrences
        window_end: End of the time window to expand occurrences
        max_instances: Maximum number of instances to return (default: 1000)

    Returns:
        Sorted list of datetime objects representing event occurrences

    Raises:
        ValueError: If recurrence_field is invalid

    Examples:
        >>> event_start = datetime(2025, 1, 1, 10, 0)
        >>> # Weekly on Tuesday and Friday, 5 times
        >>> recurrence = ["RRULE:FREQ=WEEKLY;BYDAY=TU,FR;COUNT=5"]
        >>> occurrences = expand_recurrence(
        ...     event_start, recurrence,
        ...     datetime(2025, 1, 1), datetime(2025, 2, 1)
        ... )

        >>> # Daily every 3 days with exceptions
        >>> recurrence = [
        ...     "RRULE:FREQ=DAILY;INTERVAL=3;COUNT=10",
        ...     "EXDATE:20250107T100000,20250113T100000"
        ... ]
        >>> occurrences = expand_recurrence(
        ...     event_start, recurrence,
        ...     datetime(2025, 1, 1), datetime(2025, 2, 1)
        ... )
    """
    if not recurrence_field:
        # No recurrence, return the original event if in window
        if window_start <= event_start <= window_end:
            return [event_start]
        return []

    occurrences = set()
    rrule_obj = None
    exdates = set()
    rdates = set()

    # Parse recurrence components
    for line in recurrence_field:
        line = line.strip()
        if not line:
            continue

        if line.startswith("RRULE:") or (
            not line.startswith("EXDATE:") and not line.startswith("RDATE:")
        ):
            # Parse RRULE
            rrule_str = (
                line.replace("RRULE:", "") if line.startswith("RRULE:") else line
            )
            try:
                rrule_obj = parse_rrule_string(rrule_str, event_start)
            except ValueError as e:
                raise ValueError(f"Failed to parse RRULE: {str(e)}")

        elif line.startswith("EXDATE:"):
            # Parse exception dates
            exdates.update(parse_exdates([line]))

        elif line.startswith("RDATE:"):
            # Parse additional dates
            rdates.update(parse_rdates([line]))

    # Generate occurrences from RRULE
    if rrule_obj:
        try:
            # Get occurrences within an extended window to account for events that might overlap
            # Extend window by a reasonable margin (e.g., 1 day)
            extended_start = window_start - timedelta(days=1)
            extended_end = window_end + timedelta(days=1)

            # Generate occurrences
            rule_occurrences = list(
                rrule_obj.between(extended_start, extended_end, inc=True)
            )

            # Limit the number of instances
            if len(rule_occurrences) > max_instances:
                rule_occurrences = rule_occurrences[:max_instances]

            occurrences.update(rule_occurrences)
        except Exception as e:
            raise ValueError(f"Failed to expand RRULE: {str(e)}")

    # Add RDATE occurrences
    occurrences.update(rdates)

    # Remove EXDATE occurrences
    occurrences -= exdates

    # Filter to window and sort
    filtered_occurrences = [
        dt for dt in occurrences if window_start <= dt <= window_end
    ]

    return sorted(filtered_occurrences)


def format_rrule_summary(rrule_str: str) -> str:
    """
    Generate a human-readable summary of an RRULE string.

    Args:
        rrule_str: RRULE string in RFC 5545 format

    Returns:
        Human-readable string describing the recurrence

    Examples:
        >>> format_rrule_summary("FREQ=DAILY;COUNT=5")
        "Daily, 5 times"
        >>> format_rrule_summary("FREQ=WEEKLY;BYDAY=TU,FR;COUNT=10")
        "Weekly on Tuesday, Friday, 10 times"
    """
    try:
        # Parse the RRULE parameters
        params = {}
        rrule_str = rrule_str.replace("RRULE:", "")

        for part in rrule_str.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value

        freq_map = {
            "DAILY": "Daily",
            "WEEKLY": "Weekly",
            "MONTHLY": "Monthly",
            "YEARLY": "Yearly",
        }

        day_map = {
            "MO": "Monday",
            "TU": "Tuesday",
            "WE": "Wednesday",
            "TH": "Thursday",
            "FR": "Friday",
            "SA": "Saturday",
            "SU": "Sunday",
        }

        parts = []

        # Frequency
        freq = params.get("FREQ", "")
        if freq in freq_map:
            parts.append(freq_map[freq])

        # Interval
        interval = params.get("INTERVAL")
        if interval and interval != "1":
            parts[-1] = f"Every {interval} {parts[-1].lower()}"

        # Days of week
        byday = params.get("BYDAY")
        if byday:
            days = [day_map.get(d.strip(), d) for d in byday.split(",")]
            parts.append(f"on {', '.join(days)}")

        # Count or Until
        count = params.get("COUNT")
        until = params.get("UNTIL")
        if count:
            parts.append(f"{count} times")
        elif until:
            parts.append(f"until {until}")

        return ", ".join(parts) if parts else "Custom recurrence"

    except Exception:
        return "Custom recurrence"
