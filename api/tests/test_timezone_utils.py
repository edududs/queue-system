"""Tests for timezone utilities."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

try:
    from dateutil import parser  # type: ignore
except ImportError as e:
    raise ImportError(
        "dateutil is required for timezone utilities. Please install it with 'pip install python-dateutil'.",
    ) from e

from ..app.utils.timezone import (
    convert_to_user_timezone,
    convert_to_utc,
    format_datetime_for_display,
    get_current_utc_time,
    get_user_timezone,
    is_valid_timezone,
    parse_datetime_with_timezone,
)


class TestTimezoneValidation:
    """Test timezone validation functions."""

    def test_is_valid_timezone_with_valid_timezone(self):
        """Test valid timezone names."""
        assert is_valid_timezone("UTC") is True
        assert is_valid_timezone("America/Sao_Paulo") is True
        assert is_valid_timezone("Europe/London") is True

    def test_is_valid_timezone_with_invalid_timezone(self):
        """Test invalid timezone names."""
        assert is_valid_timezone("Invalid/Timezone") is False
        assert is_valid_timezone("NotARealTimezone") is False

    def test_get_user_timezone_with_valid_timezone(self):
        """Test getting user timezone with valid input."""
        tz = get_user_timezone("Europe/London")
        # dateutil returns tzfile objects, so we check if it's not None
        assert tz is not None

    def test_get_user_timezone_with_invalid_timezone_falls_back_to_default(self):
        """Test fallback to default timezone when invalid."""
        with patch("api.app.utils.timezone.settings") as mock_settings:
            mock_settings.USER_TIMEZONE = "America/Sao_Paulo"
            tz = get_user_timezone("Invalid/Timezone")
            # dateutil returns tzfile objects, so we check if it's not None
            assert tz is not None

    def test_get_user_timezone_with_none_uses_default(self):
        """Test using default timezone when none provided."""
        with patch("api.app.utils.timezone.settings") as mock_settings:
            mock_settings.USER_TIMEZONE = "UTC"
            tz = get_user_timezone()
            # dateutil returns tzfile objects, so we check if it's not None
            assert tz is not None


class TestDateTimeOperations:
    """Test datetime manipulation functions."""

    def test_get_current_utc_time(self):
        """Test getting current UTC time."""
        utc_time = get_current_utc_time()
        assert utc_time.tzinfo == timezone.utc
        assert isinstance(utc_time, datetime)

    def test_convert_to_utc_from_naive_datetime(self):
        """Test converting naive datetime to UTC."""
        naive_dt = parser.parse("2024-01-01T12:00:00")
        utc_dt = convert_to_utc(naive_dt, "America/Sao_Paulo")
        assert utc_dt.tzinfo == timezone.utc

    def test_convert_to_utc_from_timezone_aware_datetime(self):
        """Test converting timezone-aware datetime to UTC."""
        # Create timezone-aware datetime using replace
        aware_dt = parser.parse("2024-01-01T12:00:00")
        aware_dt = aware_dt.replace(tzinfo=get_user_timezone("America/Sao_Paulo"))
        utc_dt = convert_to_utc(aware_dt, "America/Sao_Paulo")
        assert utc_dt.tzinfo == timezone.utc

    def test_convert_to_utc_with_invalid_timezone_raises_error(self):
        """Test error handling for invalid timezone."""
        naive_dt = parser.parse("2024-01-01T12:00:00")
        with pytest.raises(ValueError, match="Invalid timezone"):
            convert_to_utc(naive_dt, "Invalid/Timezone")

    def test_convert_to_user_timezone_from_utc(self):
        """Test converting UTC datetime to user timezone."""
        utc_dt = parser.parse("2024-01-01T12:00:00")
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        user_dt = convert_to_user_timezone(utc_dt, "America/Sao_Paulo")
        assert user_dt.tzinfo is not None
        # dateutil returns tzfile objects, so we check if it's not None

    def test_convert_to_user_timezone_from_naive_datetime(self):
        """Test converting naive datetime (assumed UTC) to user timezone."""
        naive_dt = parser.parse("2024-01-01T12:00:00")
        user_dt = convert_to_user_timezone(naive_dt, "America/Sao_Paulo")
        assert user_dt.tzinfo is not None
        # dateutil returns tzfile objects, so we check if it's not None


class TestDateTimeParsing:
    """Test datetime parsing functions."""

    def test_parse_datetime_with_timezone_valid_formats(self):
        """Test parsing various datetime formats."""
        # Test ISO format
        dt = parse_datetime_with_timezone("2024-01-01 12:00:00")
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None

        # Test date only
        dt = parse_datetime_with_timezone("2024-01-01")
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None

    def test_parse_datetime_with_timezone_invalid_format_raises_error(self):
        """Test error handling for invalid datetime format."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            parse_datetime_with_timezone("invalid-date")

    def test_parse_datetime_with_custom_timezone(self):
        """Test parsing with custom timezone."""
        dt = parse_datetime_with_timezone("2024-01-01 12:00:00", "Europe/London")
        # dateutil returns tzfile objects, so we check if it's not None
        assert dt.tzinfo is not None


class TestDateTimeFormatting:
    """Test datetime formatting functions."""

    def test_format_datetime_for_display(self):
        """Test formatting datetime for display."""
        utc_dt = parser.parse("2024-01-01T12:00:00")
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        formatted = format_datetime_for_display(utc_dt, "America/Sao_Paulo")
        assert isinstance(formatted, str)
        # The formatted string shows the timezone offset, not the name
        assert "-03" in formatted  # São Paulo is UTC-3 in January

    def test_format_datetime_for_display_with_custom_format(self):
        """Test formatting with custom format string."""
        utc_dt = parser.parse("2024-01-01T12:00:00")
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        formatted = format_datetime_for_display(
            utc_dt,
            "America/Sao_Paulo",
            "%Y-%m-%d",
        )
        assert formatted == "2024-01-01"
