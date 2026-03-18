"""
SFMC OAuth2 Authentication Service.

Manages the OAuth2 client_credentials flow for SFMC REST API access.
Automatically refreshes tokens before they expire.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)


class SfmcAuthService:
    def __init__(self) -> None:
        self._access_token: str | None = None
        self._token_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)

    def is_configured(self) -> bool:
        """Check if SFMC credentials are configured (non-demo mode)."""
        return bool(
            settings.sfmc_client_id
            and settings.sfmc_client_secret
            and settings.sfmc_auth_base_uri
        )

    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if not self.is_configured():
            raise RuntimeError(
                "SFMC credentials not configured. "
                "Set SFMC_CLIENT_ID, SFMC_CLIENT_SECRET, and SFMC_AUTH_BASE_URI in .env"
            )

        now = datetime.now(timezone.utc)
        if self._access_token is None or now >= self._token_expiry - timedelta(seconds=60):
            self._refresh_token()

        return self._access_token  # type: ignore[return-value]

    def _refresh_token(self) -> None:
        """Request a new access token from SFMC OAuth2 endpoint."""
        logger.info("Refreshing SFMC access token...")

        base_uri = settings.sfmc_auth_base_uri.rstrip("/")
        token_url = f"{base_uri}/v2/token"

        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.sfmc_client_id,
            "client_secret": settings.sfmc_client_secret,
        }

        try:
            resp = httpx.post(token_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            logger.info("SFMC access token refreshed, expires in %d seconds", expires_in)
        except Exception as e:
            logger.error("Failed to refresh SFMC access token: %s", e)
            raise RuntimeError(f"SFMC authentication failed: {e}") from e


# Singleton instance
sfmc_auth_service = SfmcAuthService()
