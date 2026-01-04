"""
Responsibilities:
- Convert natural language datetime expressions into timezone-aware datetime objects
- Support relative and absolute time expressions
- Remain deterministic and side-effect free
"""

from datetime import datetime, timezone
from typing import Optional
import dateparser
import logging

from app.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def parse_datetime(
    text: Optional[str],
    *,
    now: Optional[datetime] = None,
    tz: timezone = timezone.utc,
) -> Optional[datetime]:
    """
    Parse human readable datetime text into a timezone-aware datetime.

    Examples:
        "tomorrow at 5pm"
        "next monday"
        "in 2 hours"
        "jan 10 evening"

    Returns:
        datetime (timezone aware) or None if parsing fails
    """
    if not text or not text.strip():
        logger.debug("parse_datetime called with empty text")
        return None

    if not now:
        now = datetime.now(tz)

    logger.info(
        "[PARSE_DATETIME] Attempting to parse: text='%s', now='%s', tz='%s'",
        text,
        now.isoformat(),
        str(tz),
    )

    # Get timezone string - handle both timezone and ZoneInfo
    tz_str = str(tz) if hasattr(tz, "key") else tz.tzname(None)
    logger.info("[PARSE_DATETIME] Using timezone string: %s", tz_str)

    settings = {
        "RELATIVE_BASE": now,
        "TIMEZONE": tz_str,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
    }

    logger.info("[PARSE_DATETIME] dateparser settings: %s", settings)

    try:
        dt = dateparser.parse(text, settings=settings)
        logger.info("[PARSE_DATETIME] dateparser returned: %s", dt)
    except Exception as e:
        # Defensive: dateparser rarely throws, but don't trust external libs
        logger.error(
            "[PARSE_DATETIME] Date parsing exception for text='%s': %s", text, e
        )
        return None

    if not dt:
        logger.warning(
            "[PARSE_DATETIME] Date parsing returned None for text='%s'", text
        )
        return None

    # Force timezone (dateparser sometimes returns local tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
        logger.info("[PARSE_DATETIME] Added timezone to naive datetime")

    logger.info(
        "[PARSE_DATETIME] ✅ SUCCESS: '%s' -> '%s'",
        text,
        dt.isoformat(),
    )

    return dt
