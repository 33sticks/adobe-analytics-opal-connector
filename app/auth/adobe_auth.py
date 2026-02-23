"""Adobe OAuth token management for Analytics API authentication."""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
EXPIRY_BUFFER_SECONDS = 300  # 5 minutes
SCOPE = "openid,AdobeID,additional_info.projectedProductContext"


class AdobeAuthError(Exception):
    """Raised when Adobe token acquisition fails."""

    pass


class AdobeAuthManager:
    """Manages Adobe IMS OAuth access tokens with caching and auto-refresh."""

    def __init__(self, settings: Settings) -> None:
        """Initialize with settings from config (use dependency injection)."""
        self._settings = settings
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_token(self) -> str:
        """
        Return a valid access token, refreshing if expired.

        Uses a 5-minute buffer before expiry. Thread-safe via asyncio lock.
        Double-checks after acquiring lock in case another coroutine refreshed.
        """
        now = time.time()
        if self._access_token and now < self._token_expiry - EXPIRY_BUFFER_SECONDS:
            return self._access_token

        async with self._lock:
            now = time.time()
            if self._access_token and now < self._token_expiry - EXPIRY_BUFFER_SECONDS:
                return self._access_token

            token, expires_in = await self._fetch_token()
            self._access_token = token
            self._token_expiry = now + expires_in
            logger.info(
                "Adobe token acquired",
                extra={"expires_in": expires_in},
            )
            return self._access_token

    def invalidate_token(self) -> None:
        """Clear cached token to force refresh on next get_token() call."""
        self._access_token = None
        self._token_expiry = 0.0

    async def _fetch_token(self) -> tuple[str, int]:
        """
        POST to Adobe IMS token endpoint and return (access_token, expires_in).

        Raises AdobeAuthError on HTTP errors or invalid response.
        """
        body = (
            f"grant_type=client_credentials"
            f"&client_id={self._settings.adobe_client_id}"
            f"&client_secret={self._settings.adobe_client_secret}"
            f"&scope={SCOPE}"
        )
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                content=body,
                headers=headers,
            )

        if response.status_code >= 400:
            logger.error(
                "Adobe token request failed",
                extra={"status_code": response.status_code, "body": response.text[:200]},
            )
            raise AdobeAuthError(
                f"Adobe token request failed: HTTP {response.status_code}"
            )

        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in")

        if not access_token:
            raise AdobeAuthError("Adobe token response missing access_token")
        if expires_in is None:
            raise AdobeAuthError("Adobe token response missing expires_in")

        logger.debug(
            "Adobe token response received",
            extra={"status_code": response.status_code, "expires_in": expires_in},
        )
        return (access_token, int(expires_in))


_auth_manager: Optional[AdobeAuthManager] = None


def get_auth_manager() -> AdobeAuthManager:
    """Return the singleton AdobeAuthManager, lazy-initialized with get_settings()."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AdobeAuthManager(get_settings())
    return _auth_manager
