"""Opal bearer token validation for tool endpoint authentication."""

from typing import Optional

from fastapi import Header, HTTPException

from app.config import get_settings


def verify_opal_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> None:
    """Verify the Opal Bearer token from the Authorization header.

    Opal sends requests with Authorization: Bearer {OPAL_BEARER_TOKEN}.
    Returns 401 if the header is missing, malformed, or the token does not match.

    Args:
        authorization: The Authorization header value.

    Raises:
        HTTPException: 401 if missing or mismatched.
    """
    if not authorization or not authorization.strip():
        raise HTTPException(status_code=401, detail="Unauthorized")

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = parts[1]
    settings = get_settings()
    if token != settings.opal_bearer_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
