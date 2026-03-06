"""Segment insights tool — breaks down traffic by audience segment."""

import logging

from fastapi import APIRouter, Depends

from app.analytics.client import AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import (
    build_ranked_report,
    resolve_dimension,
    resolve_metric,
)
from app.analytics.response_parser import (
    get_dimension_display,
    get_metric_display,
    parse_report_response,
)
from app.metadata.registry import get_registry
from app.utils.clarification import build_segment_clarification
from app.auth.opal_auth import verify_opal_token
from app.config import get_settings
from app.tools import extract_parameters
from app.utils.date_parser import format_date_range_display, parse_date_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])

SEGMENT_MAP = {
    "mobile": "Visits_from_Mobile_Devices",
    "desktop": "Visits_from_Non-Mobile_Devices",
    "phones": "Visits_from_Phones",
    "tablet": "Visits_from_Tablets",
    "new visitors": "First_Time_Visits",
    "return visitors": "Return_Visits",
    "search": "Visits_from_Search_Engines",
    "social": "Visits_from_Social_Sites",
    "single page visits": "Single_Page_Visits",
    "non-bounces": "Non-Single_Page_Visit_(Non-Bounces)",
}

SEGMENT_EMOJI = {
    "mobile": "📱",
    "desktop": "🖥️",
    "phones": "📞",
    "tablet": "📱",
    "new visitors": "🆕",
    "return visitors": "🔄",
    "search": "🔍",
    "social": "💬",
    "single page visits": "📄",
    "non-bounces": "🔄",
}


def _capitalize_segment(segment_key: str) -> str:
    """Capitalize segment key for display (e.g. 'mobile' -> 'Mobile')."""
    return segment_key.strip().title()


@router.post("/segments", dependencies=[Depends(verify_opal_token)])
async def segment_insights(body: dict) -> dict:
    """Return traffic breakdown by audience segment from Adobe Analytics."""
    try:
        params = extract_parameters(body)
        source = (
            body.get("parameters")
            if isinstance(body.get("parameters"), dict)
            else body
        )
        source = source or {}
        segments_str = source.get("segments") or ""
        dimension = source.get("dimension") or "page"

        segments = [s.strip().lower() for s in segments_str.split(",") if s.strip()]

        if not segments:
            return {
                "status": "error",
                "message": "segments parameter is required",
                "data": {},
            }

        # Resolve segments through registry first, legacy fallback
        registry = get_registry()
        resolved_segments: list[tuple[str, str]] = []  # (display_key, segment_id)
        unknown: list[str] = []

        for s in segments:
            if registry.is_loaded:
                result = registry.resolve_segment(s)
                if result.status in ("exact", "fuzzy") and result.match:
                    resolved_segments.append((s, result.match))
                    continue
            # Legacy fallback
            if s in SEGMENT_MAP:
                resolved_segments.append((s, SEGMENT_MAP[s]))
            else:
                unknown.append(s)

        if unknown:
            # Try to provide fuzzy suggestions from registry
            if registry.is_loaded and len(unknown) == 1:
                result = registry.resolve_segment(unknown[0])
                if result.suggestions:
                    return build_segment_clarification(unknown[0], result.suggestions, ambiguous=False)
            available = ", ".join(f"'{k}'" for k in sorted(SEGMENT_MAP.keys()))
            return {
                "status": "error",
                "message": f"Unknown segment(s): {', '.join(unknown)}. Available: {available}.",
                "data": {},
            }

        top_n = min(params["top_n"], 20)
        adobe_date_range = parse_date_range(params["date_range"])
        date_range_display = format_date_range_display(params["date_range"])

        resolved_metric = resolve_metric(params["metric"])
        resolved_dimension = resolve_dimension(dimension)
        metric_display = get_metric_display(resolved_metric)
        dimension_label = get_dimension_display(resolved_dimension)

        settings = get_settings()
        client = get_analytics_client()

        segment_results: list[tuple[str, object]] = []

        for segment_key, segment_id in resolved_segments:
            request_body = build_ranked_report(
                rsid=settings.adobe_report_suite_id,
                dimension=resolved_dimension,
                metrics=[resolved_metric],
                date_range=adobe_date_range,
                limit=top_n,
                segment_id=segment_id,
            )
            response = await client.get_report(request_body)
            result = parse_report_response(
                response=response,
                metric_labels=[metric_display],
                dimension_label=dimension_label,
                date_range_display=date_range_display,
            )
            segment_results.append((segment_key, result))

        lines = [
            f"{metric_display} by segment ({date_range_display}):",
            "",
        ]
        data_segments: list[dict] = []

        for segment_key, result in segment_results:
            emoji = SEGMENT_EMOJI.get(segment_key, "")
            display_name = _capitalize_segment(segment_key)
            total = result.totals.get(metric_display, 0)
            lines.append(f"{emoji} {display_name} (Total: {total:,.0f}):")
            for i, row in enumerate(result.rows, 1):
                value = row.get(metric_display, 0)
                lines.append(f"  {i}. {row['value']} — {value:,.0f}")
            lines.append("")
            data_segments.append(
                {
                    "segment": segment_key,
                    "display_name": display_name,
                    "total": total,
                    "rows": result.rows,
                }
            )

        message = "\n".join(lines).rstrip()

        return {
            "status": "success",
            "message": message,
            "data": {
                "segments": data_segments,
                "date_range": date_range_display,
                "metric": metric_display,
            },
        }

    except ValueError as e:
        return {
            "status": "error",
            "message": f"Invalid parameter: {e}. Use 'pageviews' or 'occurrences' for metric, 'page' or 'referrer_type' for dimension.",
            "data": {},
        }
    except AdobeAnalyticsError as e:
        return {
            "status": "error",
            "message": f"Unable to retrieve segment data: {e}",
            "data": {},
        }
    except Exception:
        logger.exception("Unhandled error in segment_insights")
        return {
            "status": "error",
            "message": "An unexpected error occurred. Please try again.",
            "data": {},
        }
