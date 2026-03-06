"""Traffic validation tool — analyzes daily traffic patterns for experiment planning."""

import logging
from statistics import mean

from fastapi import APIRouter, Depends

from app.analytics.client import AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import (
    build_ranked_report,
    build_trended_report_for_page,
    resolve_metric,
)
from app.analytics.response_parser import get_metric_display, parse_report_response
from app.auth.opal_auth import verify_opal_token
from app.config import get_settings
from app.metadata.registry import get_registry
from app.utils.clarification import build_metric_clarification
from app.utils.date_parser import format_date_range_display, parse_date_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


def _extract_validation_params(body: dict) -> dict:
    """Extract validation tool parameters from Opal request body."""
    source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
    source = source or {}

    test_duration = source.get("test_duration_days", 14)
    if isinstance(test_duration, str):
        try:
            test_duration = int(test_duration)
        except (ValueError, TypeError):
            test_duration = 14

    return {
        "page_filter": source.get("page_filter"),
        "metric": source.get("metric", "pageviews"),
        "date_range": source.get("date_range", "last 30 days"),
        "test_duration_days": test_duration,
    }


def _compute_trend(daily_values: list[float]) -> str:
    """Compute trend: increasing, decreasing, or stable based on first vs second half."""
    if len(daily_values) < 2:
        return "stable"
    mid = len(daily_values) // 2
    first_half_avg = mean(daily_values[:mid])
    second_half_avg = mean(daily_values[mid:])
    if first_half_avg == 0:
        return "increasing" if second_half_avg > 0 else "stable"
    pct_change = abs(second_half_avg - first_half_avg) / first_half_avg
    if pct_change <= 0.15:
        return "stable"
    return "increasing" if second_half_avg > first_half_avg else "decreasing"


@router.post("/validation", dependencies=[Depends(verify_opal_token)])
async def traffic_validation(body: dict) -> dict:
    """Analyze daily traffic patterns for experiment planning."""
    try:
        params = _extract_validation_params(body)
        page_filter = params["page_filter"]

        if not page_filter or not str(page_filter).strip():
            return {
                "status": "error",
                "message": "page_filter is required. Specify a page name or partial match to analyze.",
                "data": {},
            }

        date_range_str = params["date_range"]
        test_duration_days = params["test_duration_days"]

        adobe_date_range = parse_date_range(date_range_str)
        date_range_display = format_date_range_display(date_range_str)

        resolved_metric = resolve_metric(params["metric"])
        metric_display = get_metric_display(resolved_metric)

        settings = get_settings()
        client = get_analytics_client()

        # Step 1: Ranked report by page to confirm page exists and get itemId
        ranked_request = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension="variables/page",
            metrics=[resolved_metric],
            date_range=adobe_date_range,
            limit=1,
            search_filter=page_filter,
        )
        ranked_response = await client.get_report(ranked_request)

        raw_rows = ranked_response.get("rows") or []
        if not raw_rows:
            return {
                "status": "success",
                "message": f"No traffic data found for pages matching '{page_filter}'. Check that the page name is correct.",
                "data": {
                    "page_filter": page_filter,
                    "date_range": date_range_display,
                    "daily_values": [],
                },
            }

        page_item_id = raw_rows[0].get("itemId")
        if not page_item_id:
            return {
                "status": "success",
                "message": f"No traffic data found for pages matching '{page_filter}'. Check that the page name is correct.",
                "data": {
                    "page_filter": page_filter,
                    "date_range": date_range_display,
                    "daily_values": [],
                },
            }

        # Step 2: Trended report filtered to this page via metricFilters
        trended_request = build_trended_report_for_page(
            rsid=settings.adobe_report_suite_id,
            metric=resolved_metric,
            date_range=adobe_date_range,
            page_item_id=str(page_item_id),
        )
        trended_response = await client.get_report(trended_request)

        result = parse_report_response(
            response=trended_response,
            metric_labels=[metric_display],
            dimension_label="Date",
            date_range_display=date_range_display,
        )

        daily_values = [row.get(metric_display, 0.0) for row in result.rows]

        if not daily_values:
            return {
                "status": "success",
                "message": f"No traffic data found for pages matching '{page_filter}'. Check that the page name is correct.",
                "data": {
                    "page_filter": page_filter,
                    "date_range": date_range_display,
                    "daily_values": [],
                },
            }

        daily_average = mean(daily_values)
        daily_min = min(daily_values)
        daily_max = max(daily_values)
        total = sum(daily_values)
        num_days = len(daily_values)
        trend = _compute_trend(daily_values)
        estimated_test_traffic = daily_average * test_duration_days

        lines = [
            f"Traffic analysis for pages matching '{page_filter}' ({date_range_display}):",
            "",
            f"- Daily average: {daily_average:,.0f} {metric_display}",
            f"- Daily range: {daily_min:,.0f} (low) to {daily_max:,.0f} (high)",
            f"- Total over {num_days} days: {total:,.0f}",
            f"- Trend: {trend}",
            "",
            f"For a {test_duration_days}-day test: ~{estimated_test_traffic:,.0f} estimated total {metric_display}",
            "",
            f"Note: This is {metric_display}, not unique visitors. Actual sample size for "
            "statistical significance depends on your conversion rate and minimum "
            "detectable effect.",
        ]
        message = "\n".join(lines)

        return {
            "status": "success",
            "message": message,
            "data": {
                "page_filter": page_filter,
                "date_range": date_range_display,
                "daily_values": daily_values,
                "daily_average": daily_average,
                "daily_min": daily_min,
                "daily_max": daily_max,
                "total": total,
                "num_days": num_days,
                "trend": trend,
                "estimated_test_traffic": estimated_test_traffic,
                "metric": metric_display,
            },
        }

    except ValueError as e:
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
        logger.exception("Unhandled error in traffic_validation")
        return {
            "status": "error",
            "message": "An unexpected error occurred. Please try again.",
            "data": {},
        }
