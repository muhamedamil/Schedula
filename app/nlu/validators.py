from datetime import datetime, timedelta, timezone
from typing import Optional
import re


#  Name Validation --------------------------------
def validate_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None

    # Reject too short or too long
    if len(name) < 2 or len(name) > 50:
        return None

    # Only allow letters, spaces, hyphens
    if not re.fullmatch(r"[A-Za-z\s\-']+", name):
        return None

    # Reject common non-name replies
    blacklist = {"yes", "yeah", "ok", "okay", "no", "sure"}
    if name.lower() in blacklist:
        return None
    return name


# Datetime Validation --------------------------------


def validate_meeting_datetime(
    meeting_datetime: Optional[datetime], *, now: datetime
) -> Optional[datetime]:
    if not meeting_datetime:
        return None

    # Both must be timezone-aware
    if meeting_datetime.tzinfo is None:
        return None

    if now.tzinfo is None:
        return None

    # Must be in the future
    if meeting_datetime <= now:
        return None

    # Reject absurd future dates (> 1 year)
    if meeting_datetime > now + timedelta(days=365):
        return None

    return meeting_datetime


# Title Validation --------------------------------


def validate_meeting_title(title: Optional[str]) -> Optional[str]:
    if not title:
        return None

    title = title.strip()

    # Length constraints
    if len(title) < 3 or len(title) > 100:
        return None

    forbidden_phrases = [
        "ignore previous",
        "system message",
        "assistant:",
        "user:",
    ]

    lowered = title.lower()
    if any(phrase in lowered for phrase in forbidden_phrases):
        return None

    return title
