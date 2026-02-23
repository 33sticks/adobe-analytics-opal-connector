"""Page comparison tool — compares page performance across two time periods."""

from datetime import timedelta

from fastapi import APIRouter, Depends

from app.analytics.client import AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import build_ranked_report, resolve_metric
from app.analytics.response_parser import METRIC_DISPLAY, parse_report_response
from app.auth.opal_auth import verify_opal_token
from app.config import get_settings
from app.tools import extract_parameters
from app.utils.date_parser import (
    format_adobe_date_range,
    format_date_bounds_display,
    format_date_range_display,
    get_date_bounds,
    parse_date_range,
)

router = APIRouter(prefix="/tools", tags=["tools"])


def calculate_prior_period(current_period: str) -> str:
    """Compute prior period by shifting current_period back by same duration."""
    start, end = get_date_bounds(current_period)
    duration = (end - start).days + 1
    prior_end = start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=duration - 1)
    return format_adobe_date_range(prior_start, prior_end)


def _format_change(current: float, prior: float) -> str:
    """Format percent change. Handles prior=0 as N/A or +∞."""
    if prior == 0:
        return "+∞" if current > 0 else "N/A"
    pct = ((current - prior) / prior) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


@router.post("/compare", dependencies=[Depends(verify_opal_token)])
async def page_comparison(body: dict) -> dict:
    """Compare page performance across current and prior time periods."""
    try:
        params = extract_parameters(body)
        source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
        source = source or {}

        pages_str = source.get("pages") or ""
        pages = [p.strip() for p in pages_str.split(",") if p.strip()]
        if not pages:
            return {
                "status": "error",
                "message": "pages parameter is required",
                "data": {},
            }

        current_period = source.get("current_period") or params["date_range"]
        prior_period = source.get("prior_period")
        if prior_period is None or (isinstance(prior_period, str) and not prior_period.strip()):
            adobe_prior_range = calculate_prior_period(current_period)
            start, end = get_date_bounds(current_period)
            duration = (end - start).days + 1
            prior_end = start - timedelta(days=1)
            prior_start = prior_end - timedelta(days=duration - 1)
            prior_display = format_date_bounds_display(prior_start, prior_end)
        else:
            prior_period = prior_period.strip() if isinstance(prior_period, str) else str(prior_period)
            adobe_prior_range = parse_date_range(prior_period)
            prior_display = format_date_range_display(prior_period)

        adobe_current_range = parse_date_range(current_period)
        current_display = format_date_range_display(current_period)

        # Safety: if prior resolved to same range as current, fall back to auto-calculation
        if adobe_current_range == adobe_prior_range:
            adobe_prior_range = calculate_prior_period(current_period)
            start, end = get_date_bounds(current_period)
            duration = (end - start).days + 1
            prior_end = start - timedelta(days=1)
            prior_start = prior_end - timedelta(days=duration - 1)
            prior_display = format_date_bounds_display(prior_start, prior_end)

        resolved_metric = resolve_metric(params["metric"])
        metric_display = METRIC_DISPLAY.get(resolved_metric, resolved_metric)

        settings = get_settings()
        client = get_analytics_client()

        rows_data: list[dict] = []
        no_data_pages: list[str] = []

        for page_name in pages:
            request_body = build_ranked_report(
                rsid=settings.adobe_report_suite_id,
                dimension="variables/page",
                metrics=[resolved_metric],
                date_range=adobe_current_range,
                limit=1,
                search_filter=page_name,
            )
            response_current = await client.get_report(request_body)
            result_current = parse_report_response(
                response=response_current,
                metric_labels=[metric_display],
                dimension_label="Page",
                date_range_display=current_display,
            )

            request_body_prior = build_ranked_report(
                rsid=settings.adobe_report_suite_id,
                dimension="variables/page",
                metrics=[resolved_metric],
                date_range=adobe_prior_range,
                limit=1,
                search_filter=page_name,
            )
            response_prior = await client.get_report(request_body_prior)
            result_prior = parse_report_response(
                response=response_prior,
                metric_labels=[metric_display],
                dimension_label="Page",
                date_range_display=prior_display,
            )

            current_val = (
                result_current.rows[0][metric_display]
                if result_current.rows
                else 0.0
            )
            prior_val = (
                result_prior.rows[0][metric_display]
                if result_prior.rows
                else 0.0
            )

            if not result_current.rows and not result_prior.rows:
                no_data_pages.append(page_name)

            change_str = _format_change(current_val, prior_val)
            rows_data.append(
                {
                    "page": page_name,
                    "current": current_val,
                    "prior": prior_val,
                    "change": change_str,
                }
            )

        header = f"Page comparison: {metric_display} ({current_display} vs {prior_display}):"
        table_lines = ["", "Page | Current | Prior | Change"]
        for r in rows_data:
            page_display = r["page"][:35] if len(r["page"]) > 35 else r["page"]
            table_lines.append(
                f"{page_display:35} | {r['current']:>7,.0f} | {r['prior']:>6,.0f} | {r['change']}"
            )
        lines = [header] + table_lines
        if no_data_pages:
            for p in no_data_pages:
                lines.append(f"No data found for '{p}'")
        message = "\n".join(lines)

        return {
            "status": "success",
            "message": message,
            "data": {
                "rows": rows_data,
                "current_period": current_display,
                "prior_period": prior_display,
                "metric": metric_display,
            },
        }

    except ValueError as e:
        return {
            "status": "error",
            "message": f"Invalid parameter: {e}. Use 'pageviews' or 'occurrences' for metric.",
            "data": {},
        }
    except AdobeAnalyticsError as e:
        return {
            "status": "error",
            "message": f"Unable to retrieve comparison data: {e}",
            "data": {},
        }
    except Exception:
        return {
            "status": "error",
            "message": "An unexpected error occurred. Please try again.",
            "data": {},
        }
