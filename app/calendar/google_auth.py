"""
Google OAuth2 Authentication for Calendar API

Responsibilities:
- Load OAuth credentials from config/.env
- Exchange refresh token for access tokens
- Provide valid credentials for Google API calls
- Surface actionable authentication errors
"""

from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.config import settings
from app.utils.logger import setup_logging  

logger = setup_logging(__name__)



class GoogleAuthError(Exception):
    """
    Raised when Google authentication or token refresh fails.

    This indicates a configuration issue, revoked credentials,
    or a Google-side outage.
    """
    pass


class GoogleAuth:
    """
    Provides Google OAuth2 credentials for Calendar API access.

    Usage:
        auth = GoogleAuth()
        creds = auth.get_credentials()
    """

    def __init__(self) -> None:
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.refresh_token = settings.GOOGLE_REFRESH_TOKEN

        self.scopes = [
            "https://www.googleapis.com/auth/calendar.events"
        ]

        self._creds: Optional[Credentials] = None

        logger.debug(
            "GoogleAuth initialized (client_id present=%s, refresh_token present=%s)",
            bool(self.client_id),
            bool(self.refresh_token),
        )
        
    # Internal helpers ------------------------------------------------------------------

    def _refresh_credentials(self) -> None:
        """
        Refresh the access token using the stored refresh token.

        This method mutates self._creds.
        """
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.error("Google OAuth credentials are missing or incomplete")
            raise GoogleAuthError(
                "Missing GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, or GOOGLE_REFRESH_TOKEN"
            )

        logger.info("Refreshing Google Calendar access token")

        self._creds = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=self.scopes,
        )

        try:
            self._creds.refresh(Request())

            if not self._creds.valid or not self._creds.token:
                logger.error("Google returned invalid credentials after refresh")
                raise GoogleAuthError("Received invalid access token from Google")

            logger.info("Google access token refreshed successfully")

        except GoogleAuthError:
            # Already logged — just re-raise
            raise

        except Exception as e:
            logger.exception("Unexpected failure during Google token refresh")
            raise GoogleAuthError(
                "Failed to refresh Google OAuth token"
            ) from e
            
    # Public API ------------------------------------------------------------------
    def get_credentials(self) -> Credentials:
        """
        Return valid Google OAuth credentials.

        Automatically refreshes the token if expired or missing.
        """
        if self._creds is None:
            logger.debug("No cached Google credentials found; refreshing")
            self._refresh_credentials()

        elif not self._creds.valid:
            logger.warning("Cached Google credentials expired; refreshing")
            self._refresh_credentials()

        return self._creds

    def get_access_token(self) -> str:
        """
        Return a valid Google OAuth access token string.
        """
        creds = self.get_credentials()

        if not creds.token:
            logger.error("Access token missing after credential refresh")
            raise GoogleAuthError("Access token unavailable")

        return creds.token
