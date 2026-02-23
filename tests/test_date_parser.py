"""
Tests for app.utils.date_parser.

Uses a fixed reference date (2026-02-22, Sunday) for deterministic results.
"""

from datetime import date
from unittest.mock import patch

import pytest

from app.utils.date_parser import (
    format_adobe_date_range,
    format_date_range_display,
    parse_date_range,
)

# Fixed reference date: Sunday, Feb 22, 2026
# - This week: Mon Feb 16 - Sat Feb 21 (yesterday)
# - Last week: Mon Feb 9 - Sun Feb 15
# - This month: Feb 1 - Feb 21
# - Last month: Jan 1 - Jan 31
FIXED_TODAY = date(2026, 2, 22)


class DateWithFixedToday(date):
    """Subclass of date that returns FIXED_TODAY from today()."""

    @classmethod
    def today(cls) -> date:
        return FIXED_TODAY


@pytest.fixture(autouse=True)
def fixed_today():
    """Patch date.today() to return FIXED_TODAY for all tests."""
    with patch("app.utils.date_parser.date", DateWithFixedToday):
        yield


class TestParseDateRange:
    """Tests for parse_date_range()."""

    def test_last_7_days(self):
        result = parse_date_range("last 7 days")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_14_days(self):
        result = parse_date_range("last 14 days")
        assert result == "2026-02-08T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_30_days(self):
        result = parse_date_range("last 30 days")
        assert result == "2026-01-23T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_90_days(self):
        result = parse_date_range("last 90 days")
        assert result == "2025-11-24T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_n_days_arbitrary(self):
        result = parse_date_range("last 3 days")
        assert result == "2026-02-19T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_1_day(self):
        result = parse_date_range("last 1 day")
        assert result == "2026-02-21T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_week(self):
        result = parse_date_range("last week")
        # Mon Feb 9 - Sun Feb 15, end exclusive = Feb 16 00:00
        assert result == "2026-02-09T00:00:00.000/2026-02-16T00:00:00.000"

    def test_prior_week_same_as_last_week(self):
        result = parse_date_range("prior week")
        assert result == "2026-02-09T00:00:00.000/2026-02-16T00:00:00.000"

    def test_previous_week_same_as_last_week(self):
        result = parse_date_range("previous week")
        assert result == "2026-02-09T00:00:00.000/2026-02-16T00:00:00.000"

    def test_this_week(self):
        result = parse_date_range("this week")
        # Mon Feb 16 - Sat Feb 21 (yesterday), end exclusive = Feb 22 00:00
        assert result == "2026-02-16T00:00:00.000/2026-02-22T00:00:00.000"

    def test_last_month(self):
        result = parse_date_range("last month")
        assert result == "2026-01-01T00:00:00.000/2026-02-01T00:00:00.000"

    def test_prior_month_same_as_last_month(self):
        result = parse_date_range("prior month")
        assert result == "2026-01-01T00:00:00.000/2026-02-01T00:00:00.000"

    def test_previous_month_same_as_last_month(self):
        result = parse_date_range("previous month")
        assert result == "2026-01-01T00:00:00.000/2026-02-01T00:00:00.000"

    def test_this_month(self):
        result = parse_date_range("this month")
        assert result == "2026-02-01T00:00:00.000/2026-02-22T00:00:00.000"

    def test_yesterday(self):
        result = parse_date_range("yesterday")
        assert result == "2026-02-21T00:00:00.000/2026-02-22T00:00:00.000"

    def test_today(self):
        result = parse_date_range("today")
        assert result == "2026-02-22T00:00:00.000/2026-02-23T00:00:00.000"

    def test_q1_2026(self):
        result = parse_date_range("Q1 2026")
        assert result == "2026-01-01T00:00:00.000/2026-04-01T00:00:00.000"

    def test_q2_2026(self):
        result = parse_date_range("Q2 2026")
        assert result == "2026-04-01T00:00:00.000/2026-07-01T00:00:00.000"

    def test_q3_2026(self):
        result = parse_date_range("Q3 2026")
        assert result == "2026-07-01T00:00:00.000/2026-10-01T00:00:00.000"

    def test_q4_2026(self):
        result = parse_date_range("Q4 2026")
        assert result == "2026-10-01T00:00:00.000/2027-01-01T00:00:00.000"

    def test_month_name_full(self):
        result = parse_date_range("February 2026")
        assert result == "2026-02-01T00:00:00.000/2026-03-01T00:00:00.000"

    def test_month_name_abbrev(self):
        result = parse_date_range("Jan 2025")
        assert result == "2025-01-01T00:00:00.000/2025-02-01T00:00:00.000"

    def test_prior_period_default_fallback(self):
        result = parse_date_range("prior period")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_previous_period_default_fallback(self):
        result = parse_date_range("previous period")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_default_fallback_unrecognized(self):
        result = parse_date_range("garbage input")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_default_fallback_last_0_days(self):
        result = parse_date_range("last 0 days")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_empty_input(self):
        result = parse_date_range("")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_whitespace_only(self):
        result = parse_date_range("   ")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_case_insensitivity_last_week(self):
        result = parse_date_range("Last Week")
        assert result == "2026-02-09T00:00:00.000/2026-02-16T00:00:00.000"

    def test_case_insensitivity_last_7_days(self):
        result = parse_date_range("LAST 7 DAYS")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_case_insensitivity_february(self):
        result = parse_date_range("FEBRUARY 2026")
        assert result == "2026-02-01T00:00:00.000/2026-03-01T00:00:00.000"

    def test_strips_whitespace(self):
        result = parse_date_range("  last 7 days  ")
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"


class TestFormatAdobeDateRange:
    """Tests for format_adobe_date_range()."""

    def test_basic_range(self):
        result = format_adobe_date_range(
            date(2026, 2, 15),
            date(2026, 2, 21),
        )
        assert result == "2026-02-15T00:00:00.000/2026-02-22T00:00:00.000"

    def test_single_day(self):
        result = format_adobe_date_range(
            date(2026, 2, 22),
            date(2026, 2, 22),
        )
        assert result == "2026-02-22T00:00:00.000/2026-02-23T00:00:00.000"


class TestFormatDateRangeDisplay:
    """Tests for format_date_range_display()."""

    def test_last_7_days(self):
        result = format_date_range_display("last 7 days")
        assert result == "Feb 15–21, 2026"

    def test_last_week(self):
        result = format_date_range_display("last week")
        assert result == "Feb 9–15, 2026"

    def test_this_week(self):
        result = format_date_range_display("this week")
        assert result == "Feb 16–21, 2026"

    def test_last_month(self):
        result = format_date_range_display("last month")
        assert result == "January 2026"

    def test_this_month(self):
        result = format_date_range_display("this month")
        assert result == "Feb 1–21, 2026"

    def test_yesterday(self):
        result = format_date_range_display("yesterday")
        assert result == "Feb 21, 2026"

    def test_today(self):
        result = format_date_range_display("today")
        assert result == "Feb 22, 2026"

    def test_q1_2026(self):
        result = format_date_range_display("Q1 2026")
        assert result == "Jan 1 – Mar 31, 2026"

    def test_february_2026(self):
        result = format_date_range_display("February 2026")
        assert result == "February 2026"

    def test_jan_2025(self):
        result = format_date_range_display("Jan 2025")
        assert result == "January 2025"

    def test_default_fallback(self):
        result = format_date_range_display("unknown")
        assert result == "Feb 15–21, 2026"

    def test_empty_input(self):
        result = format_date_range_display("")
        assert result == "Feb 15–21, 2026"
