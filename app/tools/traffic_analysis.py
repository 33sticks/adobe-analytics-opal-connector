"""Traffic analysis tool — top pages by metric (Sprint 1 stub)."""

from fastapi import APIRouter, Depends

from app.auth.opal_auth import verify_opal_token
from app.tools import extract_parameters

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/traffic", dependencies=[Depends(verify_opal_token)])
async def traffic_analysis(body: dict) -> dict:
    """Stub endpoint for traffic analysis. Full implementation in Sprint 2."""
    params = extract_parameters(body)
    metric = params["metric"]
    date_range = params["date_range"]
    top_n = params["top_n"]
    page_filter = params["page_filter"]

    page_filter_str = str(page_filter) if page_filter is not None else "None"
    message = (
        f"Traffic analysis tool received your request. Parameters: metric={metric}, "
        f"date_range={date_range}, top_n={top_n}, page_filter={page_filter_str}. "
        "Full implementation coming in Sprint 2."
    )

    return {
        "status": "success",
        "message": message,
        "data": {},
    }
