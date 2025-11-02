"""
Unit tests for recurrence utility functions.

Tests cover:
- RRULE parsing and expansion
- Weekly recurrences (TU, FR)
- Daily recurrences with intervals
- EXDATE (exception dates)
- RDATE (additional dates)
"""

import pytest
from datetime import datetime, timedelta
from app.utils.recurrence import (
    parse_rrule_string,
    parse_exdates,
    parse_rdates,
    expand_recurrence,
    format_rrule_summary,
)


class TestParseRRuleString:
    """Test RRULE string parsing."""

    def test_parse_simple_daily_rrule(self):
        """Test parsing a simple daily recurrence rule."""
        dtstart = datetime(2025, 1, 1, 10, 0)
        rrule = parse_rrule_string("FREQ=DAILY;COUNT=5", dtstart)

        occurrences = list(rrule)
        assert len(occurrences) == 5
        assert occurrences[0] == dtstart
        assert occurrences[4] == datetime(2025, 1, 5, 10, 0)

    def test_parse_weekly_rrule_with_byday(self):
        """Test parsing weekly recurrence on specific days (TU, FR)."""
        dtstart = datetime(2025, 1, 1, 10, 0)  # Wednesday
        rrule = parse_rrule_string("FREQ=WEEKLY;BYDAY=TU,FR;COUNT=5", dtstart)

        occurrences = list(rrule)
        assert len(occurrences) == 5

        # Check that occurrences fall on Tuesday (1) and Friday (4)
        for occ in occurrences:
            assert occ.weekday() in [1, 4], f"{occ} should be Tuesday or Friday"

    def test_parse_daily_with_interval(self):
        """Test parsing daily recurrence with interval."""
        dtstart = datetime(2025, 1, 1, 10, 0)
        rrule = parse_rrule_string("FREQ=DAILY;INTERVAL=3;COUNT=5", dtstart)

        occurrences = list(rrule)
        assert len(occurrences) == 5
        assert occurrences[0] == datetime(2025, 1, 1, 10, 0)
        assert occurrences[1] == datetime(2025, 1, 4, 10, 0)
        assert occurrences[2] == datetime(2025, 1, 7, 10, 0)
        assert occurrences[3] == datetime(2025, 1, 10, 10, 0)
        assert occurrences[4] == datetime(2025, 1, 13, 10, 0)

    def test_parse_rrule_with_until(self):
        """Test parsing RRULE with UNTIL parameter."""
        dtstart = datetime(2025, 1, 1, 10, 0)
        rrule = parse_rrule_string("FREQ=DAILY;UNTIL=20250105T100000", dtstart)

        occurrences = list(rrule)
        assert len(occurrences) == 5
        assert occurrences[-1] == datetime(2025, 1, 5, 10, 0)

    def test_parse_rrule_with_prefix(self):
        """Test parsing RRULE string that already has RRULE: prefix."""
        dtstart = datetime(2025, 1, 1, 10, 0)
        rrule = parse_rrule_string("RRULE:FREQ=DAILY;COUNT=3", dtstart)

        occurrences = list(rrule)
        assert len(occurrences) == 3

    def test_parse_invalid_rrule(self):
        """Test that invalid RRULE raises ValueError."""
        dtstart = datetime(2025, 1, 1, 10, 0)
        with pytest.raises(ValueError):
            parse_rrule_string("INVALID_RRULE", dtstart)

    def test_parse_empty_rrule(self):
        """Test that empty RRULE raises ValueError."""
        dtstart = datetime(2025, 1, 1, 10, 0)
        with pytest.raises(ValueError):
            parse_rrule_string("", dtstart)


class TestParseExdates:
    """Test EXDATE parsing."""

    def test_parse_single_exdate(self):
        """Test parsing a single exception date."""
        exdates = parse_exdates(["20250115T100000"])
        assert len(exdates) == 1
        assert datetime(2025, 1, 15, 10, 0) in exdates

    def test_parse_multiple_exdates(self):
        """Test parsing multiple exception dates."""
        exdates = parse_exdates(["20250115T100000", "20250122T100000"])
        assert len(exdates) == 2
        assert datetime(2025, 1, 15, 10, 0) in exdates
        assert datetime(2025, 1, 22, 10, 0) in exdates

    def test_parse_exdate_with_prefix(self):
        """Test parsing EXDATE with EXDATE: prefix."""
        exdates = parse_exdates(["EXDATE:20250115T100000"])
        assert len(exdates) == 1
        assert datetime(2025, 1, 15, 10, 0) in exdates

    def test_parse_comma_separated_exdates(self):
        """Test parsing comma-separated dates in one EXDATE line."""
        exdates = parse_exdates(
            ["EXDATE:20250115T100000,20250122T100000,20250129T100000"]
        )
        assert len(exdates) == 3
        assert datetime(2025, 1, 15, 10, 0) in exdates
        assert datetime(2025, 1, 22, 10, 0) in exdates
        assert datetime(2025, 1, 29, 10, 0) in exdates

    def test_parse_exdate_date_only(self):
        """Test parsing EXDATE with date only (no time)."""
        exdates = parse_exdates(["20250115"])
        assert len(exdates) == 1
        assert datetime(2025, 1, 15, 0, 0) in exdates

    def test_parse_empty_exdates(self):
        """Test parsing empty EXDATE list."""
        exdates = parse_exdates([])
        assert len(exdates) == 0


class TestParseRdates:
    """Test RDATE parsing."""

    def test_parse_single_rdate(self):
        """Test parsing a single additional recurrence date."""
        rdates = parse_rdates(["20250120T100000"])
        assert len(rdates) == 1
        assert datetime(2025, 1, 20, 10, 0) in rdates

    def test_parse_multiple_rdates(self):
        """Test parsing multiple additional recurrence dates."""
        rdates = parse_rdates(["20250120T100000", "20250127T100000"])
        assert len(rdates) == 2
        assert datetime(2025, 1, 20, 10, 0) in rdates
        assert datetime(2025, 1, 27, 10, 0) in rdates

    def test_parse_rdate_with_prefix(self):
        """Test parsing RDATE with RDATE: prefix."""
        rdates = parse_rdates(["RDATE:20250120T100000"])
        assert len(rdates) == 1
        assert datetime(2025, 1, 20, 10, 0) in rdates

    def test_parse_comma_separated_rdates(self):
        """Test parsing comma-separated dates in one RDATE line."""
        rdates = parse_rdates(["RDATE:20250120T100000,20250127T100000,20250203T100000"])
        assert len(rdates) == 3
        assert datetime(2025, 1, 20, 10, 0) in rdates
        assert datetime(2025, 1, 27, 10, 0) in rdates
        assert datetime(2025, 2, 3, 10, 0) in rdates


class TestExpandRecurrence:
    """Test recurrence expansion with various scenarios."""

    def test_weekly_tu_fr_count_5(self):
        """
        Test weekly recurrence on Tuesday and Friday, 5 times.
        Example: FREQ=WEEKLY;BYDAY=TU,FR;COUNT=5
        """
        event_start = datetime(2025, 1, 7, 10, 0)  # Tuesday
        recurrence = ["RRULE:FREQ=WEEKLY;BYDAY=TU,FR;COUNT=5"]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 5 occurrences on Tue/Fri
        assert len(occurrences) == 5

        # Verify all are on Tuesday (1) or Friday (4)
        for occ in occurrences:
            assert occ.weekday() in [1, 4]

        # Verify first and last occurrences
        assert occurrences[0] == datetime(2025, 1, 7, 10, 0)  # First Tuesday
        assert occurrences[1] == datetime(2025, 1, 10, 10, 0)  # First Friday

    def test_daily_interval_3(self):
        """
        Test daily recurrence with interval of 3 days.
        Example: FREQ=DAILY;INTERVAL=3;COUNT=10
        """
        event_start = datetime(2025, 1, 1, 10, 0)
        recurrence = ["RRULE:FREQ=DAILY;INTERVAL=3;COUNT=10"]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 10 occurrences
        assert len(occurrences) == 10

        # Verify 3-day intervals
        for i in range(1, len(occurrences)):
            diff = (occurrences[i] - occurrences[i - 1]).days
            assert diff == 3, f"Expected 3-day interval, got {diff}"

        # Verify specific dates
        assert occurrences[0] == datetime(2025, 1, 1, 10, 0)
        assert occurrences[1] == datetime(2025, 1, 4, 10, 0)
        assert occurrences[2] == datetime(2025, 1, 7, 10, 0)

    def test_daily_with_exdates(self):
        """
        Test daily recurrence with exception dates (EXDATE).
        Example: FREQ=DAILY;COUNT=10 with EXDATE:20250103T100000,20250107T100000
        """
        event_start = datetime(2025, 1, 1, 10, 0)
        recurrence = [
            "RRULE:FREQ=DAILY;COUNT=10",
            "EXDATE:20250103T100000,20250107T100000",
        ]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 8 occurrences (10 - 2 exceptions)
        assert len(occurrences) == 8

        # Verify exception dates are not in results
        assert datetime(2025, 1, 3, 10, 0) not in occurrences
        assert datetime(2025, 1, 7, 10, 0) not in occurrences

        # Verify other dates are present
        assert datetime(2025, 1, 1, 10, 0) in occurrences
        assert datetime(2025, 1, 2, 10, 0) in occurrences
        assert datetime(2025, 1, 4, 10, 0) in occurrences

    def test_daily_interval_3_with_exdates(self):
        """
        Test daily recurrence with interval=3 and exception dates.
        Example: FREQ=DAILY;INTERVAL=3;COUNT=10 with EXDATE
        """
        event_start = datetime(2025, 1, 1, 10, 0)
        recurrence = [
            "RRULE:FREQ=DAILY;INTERVAL=3;COUNT=10",
            "EXDATE:20250107T100000,20250113T100000",
        ]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 8 occurrences (10 - 2 exceptions)
        assert len(occurrences) == 8

        # Verify exception dates are not in results
        assert datetime(2025, 1, 7, 10, 0) not in occurrences
        assert datetime(2025, 1, 13, 10, 0) not in occurrences

        # Verify some dates are present
        assert datetime(2025, 1, 1, 10, 0) in occurrences
        assert datetime(2025, 1, 4, 10, 0) in occurrences
        assert datetime(2025, 1, 10, 10, 0) in occurrences

    def test_daily_with_rdates(self):
        """
        Test daily recurrence with additional recurrence dates (RDATE).
        Example: FREQ=DAILY;COUNT=5 with RDATE:20250120T100000,20250127T100000
        """
        event_start = datetime(2025, 1, 1, 10, 0)
        recurrence = [
            "RRULE:FREQ=DAILY;COUNT=5",
            "RDATE:20250120T100000,20250127T100000",
        ]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 7 occurrences (5 from RRULE + 2 from RDATE)
        assert len(occurrences) == 7

        # Verify RDATE additions are present
        assert datetime(2025, 1, 20, 10, 0) in occurrences
        assert datetime(2025, 1, 27, 10, 0) in occurrences

        # Verify regular recurrences are present
        assert datetime(2025, 1, 1, 10, 0) in occurrences
        assert datetime(2025, 1, 5, 10, 0) in occurrences

    def test_complex_with_exdate_and_rdate(self):
        """
        Test complex recurrence with both EXDATE and RDATE.
        Example: FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=10 with EXDATE and RDATE
        """
        event_start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        recurrence = [
            "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=10",
            "EXDATE:20250108T100000,20250115T100000",  # Remove some Wednesdays
            "RDATE:20250125T100000,20250201T100000",  # Add some Saturdays
        ]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 28, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 10 occurrences (10 from RRULE - 2 EXDATE + 2 RDATE)
        assert len(occurrences) == 10

        # Verify EXDATE removals
        assert datetime(2025, 1, 8, 10, 0) not in occurrences
        assert datetime(2025, 1, 15, 10, 0) not in occurrences

        # Verify RDATE additions
        assert datetime(2025, 1, 25, 10, 0) in occurrences
        assert datetime(2025, 2, 1, 10, 0) in occurrences

    def test_no_recurrence(self):
        """Test event with no recurrence (single occurrence)."""
        event_start = datetime(2025, 1, 15, 10, 0)
        recurrence = []
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have single occurrence
        assert len(occurrences) == 1
        assert occurrences[0] == event_start

    def test_no_recurrence_outside_window(self):
        """Test event with no recurrence outside the window."""
        event_start = datetime(2025, 3, 15, 10, 0)
        recurrence = []
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have no occurrences
        assert len(occurrences) == 0

    def test_window_filtering(self):
        """Test that occurrences are properly filtered to the window."""
        event_start = datetime(2025, 1, 1, 10, 0)
        recurrence = ["RRULE:FREQ=DAILY;COUNT=30"]
        window_start = datetime(2025, 1, 10, 0, 0)
        window_end = datetime(2025, 1, 20, 23, 59, 59)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should only have occurrences within the window
        assert all(window_start <= occ <= window_end for occ in occurrences)
        assert len(occurrences) == 11  # Jan 10-20 inclusive (at 10:00 each day)

    def test_occurrences_are_sorted(self):
        """Test that returned occurrences are sorted chronologically."""
        event_start = datetime(2025, 1, 1, 10, 0)
        recurrence = [
            "RRULE:FREQ=DAILY;COUNT=5",
            "RDATE:20250115T100000,20250110T100000",  # Add dates out of order
        ]
        window_start = datetime(2025, 1, 1, 0, 0)
        window_end = datetime(2025, 2, 1, 0, 0)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Verify occurrences are sorted
        assert occurrences == sorted(occurrences)

    def test_daily_3_days_spec(self):
        """
        Test daily recurrence for 3 days (as per spec requirement).

        Spec: Daily × 3 days
        Example: FREQ=DAILY;COUNT=3
        """
        event_start = datetime(2025, 11, 15, 10, 0)
        recurrence = ["RRULE:FREQ=DAILY;COUNT=3"]
        window_start = datetime(2025, 11, 1, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have exactly 3 occurrences
        assert len(occurrences) == 3

        # Verify the dates
        assert occurrences[0] == datetime(2025, 11, 15, 10, 0)  # Day 1
        assert occurrences[1] == datetime(2025, 11, 16, 10, 0)  # Day 2
        assert occurrences[2] == datetime(2025, 11, 17, 10, 0)  # Day 3

        # Verify all are consecutive days
        for i in range(1, len(occurrences)):
            diff = (occurrences[i] - occurrences[i - 1]).days
            assert diff == 1, f"Expected 1-day interval, got {diff} days"

    def test_weekly_2_weeks_with_exclusion_spec(self):
        """
        Test weekly recurrence for 2 weeks with one exclusion (as per spec requirement).

        Spec: Weekly × 2 weeks with exclusion
        Example: FREQ=WEEKLY;COUNT=2 with EXDATE for one occurrence
        """
        # Start on Monday
        event_start = datetime(2025, 11, 3, 14, 0)  # Monday, Nov 3
        recurrence = [
            "RRULE:FREQ=WEEKLY;COUNT=3",  # 3 weeks to test exclusion
            "EXDATE:20251110T140000",  # Exclude Nov 10 (2nd Monday)
        ]
        window_start = datetime(2025, 11, 1, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have 2 occurrences (3 from RRULE - 1 excluded)
        assert len(occurrences) == 2

        # Verify the dates
        assert datetime(2025, 11, 3, 14, 0) in occurrences  # Week 1 - Nov 3
        assert datetime(2025, 11, 10, 14, 0) not in occurrences  # Week 2 - EXCLUDED
        assert datetime(2025, 11, 17, 14, 0) in occurrences  # Week 3 - Nov 17

        # Verify all occurrences are Mondays (weekday 0)
        for occ in occurrences:
            assert occ.weekday() == 0, f"Expected Monday, got {occ.strftime('%A')}"

        # Verify 7-day interval between occurrences
        if len(occurrences) >= 2:
            diff = (occurrences[1] - occurrences[0]).days
            assert diff == 14, f"Expected 14-day interval (2 weeks), got {diff} days"

    def test_weekly_2_weeks_no_exclusion_baseline(self):
        """
        Test weekly recurrence for exactly 2 weeks without exclusion (baseline).

        Verifies basic weekly recurrence works as expected.
        """
        event_start = datetime(2025, 11, 3, 14, 0)  # Monday, Nov 3
        recurrence = ["RRULE:FREQ=WEEKLY;COUNT=2"]
        window_start = datetime(2025, 11, 1, 0, 0)
        window_end = datetime(2025, 11, 30, 23, 59)

        occurrences = expand_recurrence(
            event_start, recurrence, window_start, window_end
        )

        # Should have exactly 2 occurrences
        assert len(occurrences) == 2

        # Verify the dates
        assert occurrences[0] == datetime(2025, 11, 3, 14, 0)  # Week 1
        assert occurrences[1] == datetime(2025, 11, 10, 14, 0)  # Week 2

        # Verify 7-day interval
        diff = (occurrences[1] - occurrences[0]).days
        assert diff == 7, f"Expected 7-day interval, got {diff} days"


class TestFormatRRuleSummary:
    """Test human-readable RRULE formatting."""

    def test_format_daily_with_count(self):
        """Test formatting daily recurrence with count."""
        summary = format_rrule_summary("FREQ=DAILY;COUNT=5")
        assert "Daily" in summary
        assert "5 times" in summary

    def test_format_weekly_with_byday(self):
        """Test formatting weekly recurrence with specific days."""
        summary = format_rrule_summary("FREQ=WEEKLY;BYDAY=TU,FR;COUNT=10")
        assert "Weekly" in summary
        assert "Tuesday" in summary
        assert "Friday" in summary
        assert "10 times" in summary

    def test_format_daily_with_interval(self):
        """Test formatting daily recurrence with interval."""
        summary = format_rrule_summary("FREQ=DAILY;INTERVAL=3;COUNT=5")
        assert "Every 3" in summary
        assert "5 times" in summary

    def test_format_with_rrule_prefix(self):
        """Test formatting with RRULE: prefix."""
        summary = format_rrule_summary("RRULE:FREQ=DAILY;COUNT=5")
        assert "Daily" in summary

    def test_format_monthly(self):
        """Test formatting monthly recurrence."""
        summary = format_rrule_summary("FREQ=MONTHLY;COUNT=12")
        assert "Monthly" in summary
        assert "12 times" in summary

    def test_format_invalid_rrule(self):
        """Test formatting invalid RRULE returns default message."""
        summary = format_rrule_summary("INVALID")
        assert summary == "Custom recurrence"
