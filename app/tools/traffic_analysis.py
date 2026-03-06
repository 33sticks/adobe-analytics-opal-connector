"""Traffic analysis tool — top pages by metric."""

import logging

from fastapi import APIRouter, Depends

from app.analytics.client import AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import build_ranked_report, resolve_metric
from app.analytics.response_parser import get_metric_display, parse_report_response
from app.auth.opal_auth import verify_opal_token
from app.config import get_settings
from app.metadata.registry import get_registry
from app.tools import extract_parameters
from app.utils.clarification import build_metric_clarification
from app.utils.date_parser import format_date_range_display, parse_date_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/traffic", dependencies=[Depends(verify_opal_token)])
async def traffic_analysis(body: dict) -> dict:
    """Return top pages by metric from Adobe Analytics."""
    try:
        params = extract_parameters(body)
        date_range_str = params["date_range"]
        top_n = params["top_n"]
        page_filter = params["page_filter"]

        adobe_date_range = parse_date_range(date_range_str)
        date_range_display = format_date_range_display(date_range_str)

        resolved_metric = resolve_metric(params["metric"])
        metric_display = get_metric_display(resolved_metric)

        settings = get_settings()
        request_body = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension="variables/page",
            metrics=[resolved_metric],
            date_range=adobe_date_range,
            limit=top_n,
            search_filter=page_filter,
        )

        client = get_analytics_client()
        response = await client.get_report(request_body)

        result = parse_report_response(
            response=response,
            metric_labels=[metric_display],
            dimension_label="Page",
            date_range_display=date_range_display,
        )

        lines = [
            f"Top {result.row_count} pages by {metric_display} ({date_range_display}):",
            "",
        ]
        for i, row in enumerate(result.rows, 1):
            value = row.get(metric_display, 0)
            lines.append(f"{i}. {row['value']} — {value:,.0f}")
        lines.append("")
        total = result.totals.get(metric_display, 0)
        lines.append(
            f"Total {metric_display}: {total:,.0f} across {result.total_available} pages"
        )
        if page_filter:
            lines.append(f"Filtered to pages containing '{page_filter}'")

        message = "\n".join(lines)

        return {
            "status": "success",
            "message": message,
            "data": {
                "rows": result.rows,
                "totals": result.totals,
                "date_range": date_range_display,
                "total_pages": result.total_available,
            },
        }

    except ValueError as e:
        # Try to provide suggestions from registry
        registry = get_registry()
        if registry.is_loaded and "metric" in str(e).lower():
            result = registry.resolve_metric(params.get("metric", ""))
            if result.suggestions:
                return build_metric_clarification(params.get("metric", ""), result.suggestions, ambiguous=False)
        return {
            "status": "error",
            "message": f"Invalid parameter: {e}. Use 'pageviews' or 'occurrences' for metric.",
            "data": {},
        }
    except AdobeAnalyticsError as e:
        return {
            "status": "error",
            "message": f"Unable to retrieve traffic data: {e}",
            "data": {},
        }
    except Exception:
        logger.exception("Unhandled error in traffic_analysis")
        return {
            "status": "error",
            "message": "An unexpected error occurred. Please try again.",
            "data": {},
        }
