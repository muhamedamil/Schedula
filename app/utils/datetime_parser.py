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

    logger.debug(
        "Attempting to parse datetime from text='%s' using base='%s'",
        text,
        now.isoformat(),
    )

    settings = {
        "RELATIVE_BASE": now,
        "TIMEZONE": tz.tzname(None),
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
    }

    try:
        dt = dateparser.parse(text, settings=settings)
    except Exception as e:
        # Defensive: dateparser rarely throws, but don't trust external libs
        logger.debug("Date parsing exception for text='%s': %s", text, e)
        return None

    if not dt:
        logger.debug("Date parsing failed for text='%s'", text)
        return None

    # Force timezone (dateparser sometimes returns local tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)

    logger.debug(
        "Parsed datetime successfully: text='%s' -> '%s'",
        text,
        dt.isoformat(),
    )

    return dt
