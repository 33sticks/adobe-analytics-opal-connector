"""Schema exploration tool — lets users discover available dimensions, metrics, and segments."""

import logging

from fastapi import APIRouter, Depends

from app.auth.opal_auth import verify_opal_token
from app.metadata.registry import get_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/schema", dependencies=[Depends(verify_opal_token)])
async def schema_exploration(body: dict) -> dict:
    """Return available dimensions, metrics, and segments from the registry."""
    try:
        source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
        source = source or {}

        # Optional filter: "dimensions", "metrics", "segments", or None for all
        category = source.get("category", "all").lower()
        search = source.get("search", "").strip().lower()

        registry = get_registry()
        if not registry.is_loaded:
            return {
                "status": "error",
                "message": "Metadata schema not loaded. Run extract_metadata.py first.",
                "data": {},
            }

        result: dict = {}
        lines: list[str] = []

        if category in ("all", "dimensions"):
            dims = registry.list_dimensions()
            if search:
                dims = [d for d in dims if search in d["name"].lower() or search in d["id"].lower()]
            result["dimensions"] = dims
            lines.append(f"Dimensions ({len(dims)}):")
            for d in dims:
                lines.append(f"  - {d['name']} ({d['id']})")
            lines.append("")

        if category in ("all", "metrics"):
            mets = registry.list_metrics()
            if search:
                mets = [m for m in mets if search in m["name"].lower() or search in m["id"].lower()]
            result["metrics"] = mets
            lines.append(f"Metrics ({len(mets)}):")
            for m in mets:
                lines.append(f"  - {m['name']} ({m['id']})")
            lines.append("")

        if category in ("all", "segments"):
            segs = registry.list_segments()
            if search:
                segs = [s for s in segs if search in s["name"].lower() or search in s["id"].lower()]
            result["segments"] = segs
            lines.append(f"Segments ({len(segs)}):")
            for s in segs:
                lines.append(f"  - {s['name']} ({s['id']})")

        message = "\n".join(lines).rstrip()
        if not message:
            message = f"No results found for search '{search}'." if search else "No metadata available."

        return {
            "status": "success",
            "message": message,
            "data": result,
        }

    except Exception:
        logger.exception("Unhandled error in schema_exploration")
        return {"status": "error", "message": "An unexpected error occurred.", "data": {}}
