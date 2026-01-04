"""
Google Calendar Event Creation Service

Responsibilities:
- Create calendar events using Google Calendar API
- Handle retries and transient failures
- Surface clear, domain-specific errors
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.calendar.google_auth import GoogleAuth, GoogleAuthError
from app.config import settings

logger = logging.getLogger(__name__)


class GoogleCalendarError(Exception):
    """
    Raised when calendar event creation fails.
    """

    pass


class GoogleCalendarService:
    """
    Production-grade Google Calendar service.

    Usage:
        calendar = GoogleCalendarService()
        event = await calendar.create_event(...)
    """

    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID

    # Public async API -----------------------------------------------------------------

    async def create_event(
        self,
        *,
        title: str,
        start_datetime: datetime,
        duration_minutes: int = 30,
        description: Optional[str] = None,
        timezone: str = "Asia/Kolkata",
        retries: int = 2,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Google Calendar event.

        Args:
            access_token: Optional user's Google OAuth access token. If provided,
                         creates the event in that user's calendar instead of using
                         environment variables.

        Returns:
            Dict containing event_id, html_link, status
        """
        if not title:
            raise GoogleCalendarError("Event title is required")

        if not isinstance(start_datetime, datetime):
            raise GoogleCalendarError("start_datetime must be a datetime object")

        loop = asyncio.get_running_loop()

        for attempt in range(1, retries + 1):
            try:
                return await loop.run_in_executor(
                    self._executor,
                    self._create_event_blocking,
                    title,
                    start_datetime,
                    duration_minutes,
                    description,
                    timezone,
                    access_token,
                )

            except GoogleCalendarError:
                raise  # already logged

            except Exception as e:
                logger.exception("Calendar event creation failed (attempt %s)", attempt)

        raise GoogleCalendarError("Failed to create calendar event after retries")

    # Internal blocking implementation ------------------------------------------------------------

    def _create_event_blocking(
        self,
        title: str,
        start_datetime: datetime,
        duration_minutes: int,
        description: Optional[str],
        timezone: str,
        access_token: Optional[str],
    ) -> Dict[str, Any]:
        """
        Blocking Google Calendar API call.
        """
        try:
            # Pass the access_token to GoogleAuth
            auth = GoogleAuth(access_token=access_token)
            creds = auth.get_credentials()
        except GoogleAuthError as e:
            logger.error("Google auth failed: %s", e)
            raise GoogleCalendarError("Authentication with Google failed") from e

        end_datetime = start_datetime + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": title,
            "description": description or "",
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": timezone,
            },
        }

        logger.info(
            "Creating calendar event: title=%s start=%s",
            title,
            start_datetime.isoformat(),
        )

        try:
            service = build(
                "calendar",
                "v3",
                credentials=creds,
                cache_discovery=False,
            )

            event = (
                service.events()
                .insert(
                    calendarId=self.calendar_id,
                    body=event_body,
                )
                .execute()
            )

            logger.info(
                "Calendar event created successfully (event_id=%s)",
                event.get("id"),
            )

            return {
                "event_id": event.get("id"),
                "html_link": event.get("htmlLink"),
                "status": event.get("status"),
            }

        except HttpError as e:
            logger.exception("Google Calendar API error")
            raise GoogleCalendarError(f"Google Calendar API error: {e}") from e

        except Exception as e:
            logger.exception("Unexpected calendar error")
            raise GoogleCalendarError(
                "Unexpected error while creating calendar event"
            ) from e
