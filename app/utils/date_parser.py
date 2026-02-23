"""
Natural language date range parsing for Adobe Analytics.

Converts natural language date references into Adobe's ISO 8601 date range format
and human-readable display strings. Uses python-dateutil and stdlib only.
No imports from app modules.
"""

import calendar
import re
from datetime import date, timedelta

# Month name lookup: full names and abbreviations -> month number (1-12)
_MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

# Quarter number -> (start_month, end_month)
_QUARTER_MONTHS: dict[int, tuple[int, int]] = {
    1: (1, 3),
    2: (4, 6),
    3: (7, 9),
    4: (10, 12),
}


def format_adobe_date_range(start: date, end: date) -> str:
    """
    Format two date objects as Adobe Analytics ISO 8601 date range.

    Start is inclusive (00:00:00.000 of start date).
    End is exclusive — Adobe expects 00:00:00.000 of the day AFTER the last
    inclusive day.

    Args:
        start: Inclusive start date.
        end: Inclusive end date (last day of range).

    Returns:
        String in format "YYYY-MM-DDTHH:MM:SS.000/YYYY-MM-DDTHH:MM:SS.000".
    """
    start_str = f"{start.isoformat()}T00:00:00.000"
    end_exclusive = end + timedelta(days=1)
    end_str = f"{end_exclusive.isoformat()}T00:00:00.000"
    return f"{start_str}/{end_str}"


def _parse_to_dates(date_range: str) -> tuple[date, date]:
    """
    Parse natural language date range to (start_date, end_date).

    Both dates are inclusive. Returns (start, end) for the requested range.
    Uses date.today() as reference. Case-insensitive, strips whitespace.
    """
    s = date_range.strip().lower()
    today = date.today()

    # Empty or unrecognized -> default to last 7 days
    def default_range() -> tuple[date, date]:
        return (today - timedelta(days=7), today - timedelta(days=1))

    if not s:
        return default_range()

    # 1. last N days
    m = re.match(r"last\s+(\d+)\s+days?$", s)
    if m:
        n = int(m.group(1))
        if n >= 1:
            end = today - timedelta(days=1)
            start = today - timedelta(days=n)
            return (start, end)

    # 2. last week, this week
    if s == "last week":
        # Monday of prior week through Sunday of prior week
        # today.weekday() -> Monday=0, Sunday=6
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)
        return (last_monday, last_sunday)

    if s == "this week":
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        return (this_monday, today - timedelta(days=1))

    # 3. last month, this month
    if s == "last month":
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        first_of_last_month = last_of_last_month.replace(day=1)
        return (first_of_last_month, last_of_last_month)

    if s == "this month":
        first_of_this_month = today.replace(day=1)
        return (first_of_this_month, today - timedelta(days=1))

    # 4. yesterday, today
    if s == "yesterday":
        yesterday = today - timedelta(days=1)
        return (yesterday, yesterday)

    if s == "today":
        return (today, today)

    # 5. Q1 2026 ... Q4 2026
    m = re.match(r"q([1-4])\s+(\d{4})$", s)
    if m:
        q = int(m.group(1))
        year = int(m.group(2))
        start_month, end_month = _QUARTER_MONTHS[q]
        start_d = date(year, start_month, 1)
        _, last_day = calendar.monthrange(year, end_month)
        end_d = date(year, end_month, last_day)
        return (start_d, end_d)

    # 6. February 2026, Jan 2025
    m = re.match(r"(\w+)\s+(\d{4})$", s)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        if month_str in _MONTH_NAMES:
            month_num = _MONTH_NAMES[month_str]
            start_d = date(year, month_num, 1)
            _, last_day = calendar.monthrange(year, month_num)
            end_d = date(year, month_num, last_day)
            return (start_d, end_d)

    return default_range()


def parse_date_range(date_range: str) -> str:
    """
    Convert natural language date range to Adobe Analytics ISO 8601 format.

    Args:
        date_range: Natural language string like "last 7 days", "last week",
            "this month", "February 2026", "Q1 2026", etc.

    Returns:
        Adobe format "YYYY-MM-DDTHH:MM:SS.000/YYYY-MM-DDTHH:MM:SS.000".
        Start is inclusive, end is exclusive.
    """
    start, end = _parse_to_dates(date_range)
    return format_adobe_date_range(start, end)


def _is_full_month(start: date, end: date) -> bool:
    """True if range is exactly a full calendar month."""
    if start.day != 1:
        return False
    _, last_day = calendar.monthrange(start.year, start.month)
    return end == date(start.year, start.month, last_day)


def _is_full_quarter(start: date, end: date) -> bool:
    """True if range is exactly a full calendar quarter."""
    if start.day != 1:
        return False
    q = (start.month - 1) // 3 + 1
    end_month = q * 3
    _, last_day = calendar.monthrange(start.year, end_month)
    return end == date(start.year, end_month, last_day)


def format_date_range_display(date_range: str) -> str:
    """
    Convert natural language date range to human-readable display string.

    Args:
        date_range: Natural language string (same as parse_date_range).

    Returns:
        Friendly string like "Feb 10–16, 2026", "January 2026",
        "Jan 1 – Mar 31, 2026", or "Feb 22, 2026".
    """
    start, end = _parse_to_dates(date_range)

    # Single day
    if start == end:
        return f"{start.strftime('%b')} {start.day}, {start.year}"

    # Full month
    if _is_full_month(start, end):
        return start.strftime("%B %Y")

    # Full quarter
    if _is_full_quarter(start, end):
        return f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}, {end.year}"

    # Same month
    if start.month == end.month and start.year == end.year:
        return f"{start.strftime('%b')} {start.day}–{end.day}, {end.year}"

    # Different months
    return f"{start.strftime('%b')} {start.day}, {start.year} – {end.strftime('%b')} {end.day}, {end.year}"
