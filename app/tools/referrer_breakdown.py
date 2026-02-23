"""Referrer breakdown tool — traffic by referrer type (Sprint 1 stub)."""

from fastapi import APIRouter, Depends

from app.auth.opal_auth import verify_opal_token
from app.tools import extract_parameters

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/referrers", dependencies=[Depends(verify_opal_token)])
async def referrer_breakdown(body: dict) -> dict:
    """Stub endpoint for referrer breakdown. Full implementation in Sprint 2."""
    params = extract_parameters(body)
    metric = params["metric"]
    date_range = params["date_range"]

    message = (
        f"Referrer breakdown tool received your request. Parameters: metric={metric}, "
        f"date_range={date_range}. Full implementation coming in Sprint 2."
    )

    return {
        "status": "success",
        "message": message,
        "data": {},
    }
