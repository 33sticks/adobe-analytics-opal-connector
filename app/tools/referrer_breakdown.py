"""Referrer breakdown tool — traffic by referrer type."""

from fastapi import APIRouter, Depends

from app.analytics.client import AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import build_ranked_report, resolve_metric
from app.analytics.response_parser import METRIC_DISPLAY, parse_report_response
from app.auth.opal_auth import verify_opal_token
from app.config import get_settings
from app.tools import extract_parameters
from app.utils.date_parser import format_date_range_display, parse_date_range

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/referrers", dependencies=[Depends(verify_opal_token)])
async def referrer_breakdown(body: dict) -> dict:
    """Return traffic breakdown by referrer type from Adobe Analytics."""
    try:
        params = extract_parameters(body)
        date_range_str = params["date_range"]

        adobe_date_range = parse_date_range(date_range_str)
        date_range_display = format_date_range_display(date_range_str)

        resolved_metric = resolve_metric(params["metric"])
        metric_display = METRIC_DISPLAY.get(resolved_metric, resolved_metric)

        settings = get_settings()
        request_body = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension="variables/referrertype",
            metrics=[resolved_metric],
            date_range=adobe_date_range,
            limit=20,
        )

        client = get_analytics_client()
        response = await client.get_report(request_body)

        result = parse_report_response(
            response=response,
            metric_labels=[metric_display],
            dimension_label="Referrer Type",
            date_range_display=date_range_display,
        )

        total = result.totals.get(metric_display, 0)
        lines = [
            f"Traffic breakdown by Referrer Type ({date_range_display}):",
            "",
        ]
        for row in result.rows:
            value = row.get(metric_display, 0)
            percentage = (value / total * 100) if total else 0.0
            lines.append(f"- {row['value']}: {value:,.0f} ({percentage:.1f}%)")
        lines.append("")
        lines.append(f"Total {metric_display}: {total:,.0f}")

        message = "\n".join(lines)

        return {
            "status": "success",
            "message": message,
            "data": {
                "rows": result.rows,
                "totals": result.totals,
                "date_range": date_range_display,
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
            "message": f"Unable to retrieve traffic data: {e}",
            "data": {},
        }
    except Exception:
        return {
            "status": "error",
            "message": "An unexpected error occurred. Please try again.",
            "data": {},
        }
