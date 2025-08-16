"""Timezone utilities for the Queue System API.

This module provides timezone-aware datetime operations using python-dateutil.
Each function is idempotent, takes parameters and returns results in a simple manner.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

try:
    from dateutil import parser, tz  # type: ignore
except ImportError as e:
    raise ImportError(
        "python-dateutil is required for timezone utilities. "
        "Please install it with 'pip install python-dateutil'.",
    ) from e

from ..settings.config import settings

logger = logging.getLogger(__name__)


def is_valid_timezone(timezone_name: str) -> bool:
    """Check if a timezone name is valid.

    Args:
        timezone_name: The timezone name to validate

    Returns:
        True if valid, False otherwise

    """
    tz_obj = tz.gettz(timezone_name)
    if tz_obj is None:
        logger.warning(f"Invalid timezone: {timezone_name}")
        return False
    return True


def get_user_timezone(user_timezone: Optional[str] = None):
    """Get the user's timezone, falling back to default if invalid.

    Args:
        user_timezone: Optional user timezone, defaults to settings.USER_TIMEZONE

    Returns:
        timezone object

    """
    if user_timezone and is_valid_timezone(user_timezone):
        return tz.gettz(user_timezone)

    return tz.gettz(settings.USER_TIMEZONE)


def get_current_utc_time() -> datetime:
    """Get current UTC time with timezone info.

    Returns:
        Current UTC datetime with timezone

    """
    return datetime.now(timezone.utc)


def convert_to_utc(dt: datetime, source_timezone: str) -> datetime:
    """Convert datetime from source timezone to UTC.

    Args:
        dt: Datetime to convert (naive or timezone-aware)
        source_timezone: Source timezone name

    Returns:
        UTC datetime with timezone info

    Raises:
        ValueError: If source_timezone is invalid

    """
    if not is_valid_timezone(source_timezone):
        raise ValueError(f"Invalid timezone: {source_timezone}")

    source_tz = tz.gettz(source_timezone)

    # If datetime is naive, assume it's in source timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=source_tz)

    return dt.astimezone(timezone.utc)


def convert_to_user_timezone(
    dt: datetime,
    target_timezone: Optional[str] = None,
) -> datetime:
    """Convert UTC datetime to user timezone.

    Args:
        dt: UTC datetime to convert
        target_timezone: Target timezone, defaults to settings.USER_TIMEZONE

    Returns:
        Datetime in target timezone

    Raises:
        ValueError: If target_timezone is invalid

    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)

    target_tz = get_user_timezone(target_timezone)
    return dt.astimezone(target_tz)


def parse_datetime_with_timezone(
    dt_str: str,
    timezone_name: Optional[str] = None,
) -> datetime:
    """Parse datetime string and apply timezone using dateutil.parser.

    Args:
        dt_str: Datetime string to parse
        timezone_name: Timezone to apply, defaults to settings.USER_TIMEZONE

    Returns:
        Parsed datetime with timezone info

    Raises:
        ValueError: If datetime string is invalid or timezone is invalid

    """
    try:
        # Use dateutil.parser for intelligent parsing
        dt = parser.parse(dt_str)

        # Apply timezone if specified
        if timezone_name:
            target_tz = get_user_timezone(timezone_name)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=target_tz)
            else:
                dt = dt.astimezone(target_tz)
        elif dt.tzinfo is None:
            # If no timezone specified and datetime is naive, use default
            target_tz = get_user_timezone()
            dt = dt.replace(tzinfo=target_tz)

        return dt

    except Exception as e:
        logger.error(f"Error parsing datetime {dt_str}: {e}")
        raise ValueError(f"Invalid datetime format: {dt_str}") from e


def format_datetime_for_display(
    dt: datetime,
    target_timezone: Optional[str] = None,
    format_str: str = "%Y-%m-%d %H:%M:%S %Z",
) -> str:
    """Format datetime for display in user timezone.

    Args:
        dt: Datetime to format
        target_timezone: Target timezone, defaults to settings.USER_TIMEZONE
        format_str: Format string for display

    Returns:
        Formatted datetime string

    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)

    target_tz = get_user_timezone(target_timezone)
    localized_dt = dt.astimezone(target_tz)

    return localized_dt.strftime(format_str)


def get_timezone_offset(timezone_name: str) -> str:
    """Get timezone offset as string (e.g., '+03:00', '-05:00').

    Args:
        timezone_name: Timezone name

    Returns:
        Timezone offset string

    """
    if not is_valid_timezone(timezone_name):
        raise ValueError(f"Invalid timezone: {timezone_name}")

    tz_obj = tz.gettz(timezone_name)
    now = datetime.now(tz_obj)
    offset = now.strftime("%z")

    # Format as +HH:MM or -HH:MM
    return f"{offset[:3]}:{offset[3:]}"


def is_dst_active(timezone_name: str) -> bool:
    """Check if Daylight Saving Time is active in the given timezone.

    Args:
        timezone_name: Timezone name

    Returns:
        True if DST is active, False otherwise

    """
    if not is_valid_timezone(timezone_name):
        raise ValueError(f"Invalid timezone: {timezone_name}")

    tz_obj = tz.gettz(timezone_name)
    now = datetime.now(tz_obj)

    # Check if current time is in DST
    dst_info = now.dst()
    return bool(dst_info and dst_info.total_seconds() > 0)
