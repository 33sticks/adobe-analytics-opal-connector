"""General-purpose query tool — ranked, trend, and compare endpoints."""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends

from app.analytics.client import AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import build_ranked_report, build_trended_report
from app.analytics.response_parser import (
    get_dimension_display,
    get_metric_display,
    parse_report_response,
)
from app.auth.opal_auth import verify_opal_token
from app.config import get_settings
from app.metadata.registry import get_registry
from app.utils.date_parser import (
    format_adobe_date_range,
    format_date_bounds_display,
    format_date_range_display,
    get_date_bounds,
    parse_date_range,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


def _resolve_with_clarification(name: str, kind: str):
    """Resolve a name through the registry. Returns Adobe ID string or clarification dict."""
    registry = get_registry()
    if not registry.is_loaded:
        # Fall back to query_builder's resolve functions
        return name

    if kind == "dimension":
        result = registry.resolve_dimension(name)
    elif kind == "metric":
        result = registry.resolve_metric(name)
    elif kind == "segment":
        result = registry.resolve_segment(name)
    else:
        return name

    if result.status in ("exact", "fuzzy") and result.match:
        return result.match

    if result.status == "ambiguous" and result.suggestions:
        return {
            "status": "clarification_needed",
            "message": result.message or f"Ambiguous {kind}: '{name}'",
            "data": {
                "clarification_type": f"ambiguous_{kind}",
                "input": name,
                "options": result.suggestions,
            },
        }

    return {
        "status": "clarification_needed",
        "message": result.message or f"Unknown {kind}: '{name}'",
        "data": {
            "clarification_type": f"unrecognized_{kind}",
            "input": name,
            "options": result.suggestions or [],
        },
    }


@router.post("/query", dependencies=[Depends(verify_opal_token)])
async def general_query(body: dict) -> dict:
    """General-purpose ranked query: any dimension + metric(s) + optional segment/filter."""
    try:
        source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
        source = source or {}

        dimension_name = source.get("dimension", "page")
        metrics_str = source.get("metrics", source.get("metric", "pageviews"))
        segment_name = source.get("segment")
        date_range_str = source.get("date_range", "last 7 days")
        search_filter = source.get("filter", source.get("page_filter"))
        top_n = source.get("top_n", 10)
        if isinstance(top_n, str):
            try:
                top_n = int(top_n)
            except (ValueError, TypeError):
                top_n = 10
        top_n = min(top_n, 50)

        # Resolve dimension
        dim_resolved = _resolve_with_clarification(dimension_name, "dimension")
        if isinstance(dim_resolved, dict):
            return dim_resolved

        # Resolve metrics
        if isinstance(metrics_str, str):
            metric_names = [m.strip() for m in metrics_str.split(",") if m.strip()]
        elif isinstance(metrics_str, list):
            metric_names = metrics_str
        else:
            metric_names = ["pageviews"]

        resolved_metrics = []
        for m in metric_names:
            met_resolved = _resolve_with_clarification(m, "metric")
            if isinstance(met_resolved, dict):
                return met_resolved
            resolved_metrics.append(met_resolved)

        # Resolve segment
        segment_id = None
        if segment_name:
            seg_resolved = _resolve_with_clarification(segment_name, "segment")
            if isinstance(seg_resolved, dict):
                return seg_resolved
            segment_id = seg_resolved

        adobe_date_range = parse_date_range(date_range_str)
        date_range_display = format_date_range_display(date_range_str)

        metric_displays = [get_metric_display(m) for m in resolved_metrics]
        dimension_label = get_dimension_display(dim_resolved)

        settings = get_settings()
        request_body = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension=dim_resolved,
            metrics=resolved_metrics,
            date_range=adobe_date_range,
            limit=top_n,
            search_filter=search_filter,
            segment_id=segment_id,
        )

        client = get_analytics_client()
        response = await client.get_report(request_body)

        result = parse_report_response(
            response=response,
            metric_labels=metric_displays,
            dimension_label=dimension_label,
            date_range_display=date_range_display,
        )

        # Format message
        primary_metric = metric_displays[0]
        lines = [
            f"Top {result.row_count} {dimension_label} by {primary_metric} ({date_range_display}):",
            "",
        ]
        for i, row in enumerate(result.rows, 1):
            parts = [f"{i}. {row['value']}"]
            for md in metric_displays:
                val = row.get(md, 0)
                parts.append(f"{md}: {val:,.0f}")
            lines.append(" — ".join(parts))

        lines.append("")
        for md in metric_displays:
            total = result.totals.get(md, 0)
            lines.append(f"Total {md}: {total:,.0f}")
        lines.append(f"{result.total_available} total {dimension_label} values")

        if segment_name:
            lines.append(f"Segment: {segment_name}")
        if search_filter:
            lines.append(f"Filtered to: '{search_filter}'")

        return {
            "status": "success",
            "message": "\n".join(lines),
            "data": {
                "rows": result.rows,
                "totals": result.totals,
                "date_range": date_range_display,
                "dimension": dimension_label,
                "metrics": metric_displays,
                "total_available": result.total_available,
            },
        }

    except ValueError as e:
        return {"status": "error", "message": f"Invalid parameter: {e}", "data": {}}
    except AdobeAnalyticsError as e:
        return {"status": "error", "message": f"Adobe Analytics error: {e}", "data": {}}
    except Exception:
        logger.exception("Unhandled error in general_query")
        return {"status": "error", "message": "An unexpected error occurred. Please try again.", "data": {}}


@router.post("/query/trend", dependencies=[Depends(verify_opal_token)])
async def trend_query(body: dict) -> dict:
    """Time-series for any metric, with optional segment/filter and granularity."""
    try:
        source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
        source = source or {}

        metric_name = source.get("metric", "pageviews")
        segment_name = source.get("segment")
        date_range_str = source.get("date_range", "last 30 days")
        search_filter = source.get("filter", source.get("page_filter"))
        granularity = source.get("granularity", "day")

        # Map granularity to dimension
        granularity_map = {
            "day": "variables/daterangeday",
            "week": "variables/daterangeweek",
            "month": "variables/daterangemonth",
        }
        time_dimension = granularity_map.get(granularity.lower(), "variables/daterangeday")

        # Resolve metric
        met_resolved = _resolve_with_clarification(metric_name, "metric")
        if isinstance(met_resolved, dict):
            return met_resolved

        # Resolve segment
        segment_id = None
        if segment_name:
            seg_resolved = _resolve_with_clarification(segment_name, "segment")
            if isinstance(seg_resolved, dict):
                return seg_resolved
            segment_id = seg_resolved

        adobe_date_range = parse_date_range(date_range_str)
        date_range_display = format_date_range_display(date_range_str)
        metric_display = get_metric_display(met_resolved)

        settings = get_settings()
        request_body = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension=time_dimension,
            metrics=[met_resolved],
            date_range=adobe_date_range,
            limit=400,
            search_filter=search_filter,
            segment_id=segment_id,
        )

        client = get_analytics_client()
        response = await client.get_report(request_body)

        time_label = granularity.title()
        result = parse_report_response(
            response=response,
            metric_labels=[metric_display],
            dimension_label=time_label,
            date_range_display=date_range_display,
        )

        values = [row.get(metric_display, 0.0) for row in result.rows]
        total = sum(values)

        lines = [
            f"{metric_display} trend by {granularity} ({date_range_display}):",
            "",
        ]
        for row in result.rows:
            val = row.get(metric_display, 0)
            lines.append(f"  {row['value']}: {val:,.0f}")
        lines.append("")
        lines.append(f"Total: {total:,.0f} over {len(values)} {granularity}s")

        return {
            "status": "success",
            "message": "\n".join(lines),
            "data": {
                "rows": result.rows,
                "total": total,
                "date_range": date_range_display,
                "metric": metric_display,
                "granularity": granularity,
                "data_points": len(values),
            },
        }

    except ValueError as e:
        return {"status": "error", "message": f"Invalid parameter: {e}", "data": {}}
    except AdobeAnalyticsError as e:
        return {"status": "error", "message": f"Adobe Analytics error: {e}", "data": {}}
    except Exception:
        logger.exception("Unhandled error in trend_query")
        return {"status": "error", "message": "An unexpected error occurred. Please try again.", "data": {}}


@router.post("/query/compare", dependencies=[Depends(verify_opal_token)])
async def compare_query(body: dict) -> dict:
    """Period-over-period comparison for any dimension/metric combination."""
    try:
        source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
        source = source or {}

        dimension_name = source.get("dimension", "page")
        metric_name = source.get("metric", "pageviews")
        segment_name = source.get("segment")
        current_period = source.get("current_period", source.get("date_range", "last 7 days"))
        prior_period = source.get("prior_period")
        search_filter = source.get("filter", source.get("page_filter"))
        top_n = source.get("top_n", 10)
        if isinstance(top_n, str):
            try:
                top_n = int(top_n)
            except (ValueError, TypeError):
                top_n = 10
        top_n = min(top_n, 50)

        # Resolve dimension
        dim_resolved = _resolve_with_clarification(dimension_name, "dimension")
        if isinstance(dim_resolved, dict):
            return dim_resolved

        # Resolve metric
        met_resolved = _resolve_with_clarification(metric_name, "metric")
        if isinstance(met_resolved, dict):
            return met_resolved

        # Resolve segment
        segment_id = None
        if segment_name:
            seg_resolved = _resolve_with_clarification(segment_name, "segment")
            if isinstance(seg_resolved, dict):
                return seg_resolved
            segment_id = seg_resolved

        # Current period
        adobe_current_range = parse_date_range(current_period)
        current_display = format_date_range_display(current_period)

        # Prior period — auto-calculate if not specified
        if prior_period and isinstance(prior_period, str) and prior_period.strip():
            adobe_prior_range = parse_date_range(prior_period)
            prior_display = format_date_range_display(prior_period)
        else:
            start, end = get_date_bounds(current_period)
            duration = (end - start).days + 1
            prior_end = start - timedelta(days=1)
            prior_start = prior_end - timedelta(days=duration - 1)
            adobe_prior_range = format_adobe_date_range(prior_start, prior_end)
            prior_display = format_date_bounds_display(prior_start, prior_end)

        # Safety: don't compare same range
        if adobe_current_range == adobe_prior_range:
            start, end = get_date_bounds(current_period)
            duration = (end - start).days + 1
            prior_end = start - timedelta(days=1)
            prior_start = prior_end - timedelta(days=duration - 1)
            adobe_prior_range = format_adobe_date_range(prior_start, prior_end)
            prior_display = format_date_bounds_display(prior_start, prior_end)

        metric_display = get_metric_display(met_resolved)
        dimension_label = get_dimension_display(dim_resolved)

        settings = get_settings()
        client = get_analytics_client()

        # Current period report
        current_request = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension=dim_resolved,
            metrics=[met_resolved],
            date_range=adobe_current_range,
            limit=top_n,
            search_filter=search_filter,
            segment_id=segment_id,
        )
        current_response = await client.get_report(current_request)
        current_result = parse_report_response(
            response=current_response,
            metric_labels=[metric_display],
            dimension_label=dimension_label,
            date_range_display=current_display,
        )

        # Prior period report
        prior_request = build_ranked_report(
            rsid=settings.adobe_report_suite_id,
            dimension=dim_resolved,
            metrics=[met_resolved],
            date_range=adobe_prior_range,
            limit=top_n,
            search_filter=search_filter,
            segment_id=segment_id,
        )
        prior_response = await client.get_report(prior_request)
        prior_result = parse_report_response(
            response=prior_response,
            metric_labels=[metric_display],
            dimension_label=dimension_label,
            date_range_display=prior_display,
        )

        # Build comparison
        prior_lookup = {row["value"]: row.get(metric_display, 0) for row in prior_result.rows}
        rows_data = []
        for row in current_result.rows:
            current_val = row.get(metric_display, 0)
            prior_val = prior_lookup.get(row["value"], 0)
            if prior_val == 0:
                change = "+∞" if current_val > 0 else "N/A"
            else:
                pct = ((current_val - prior_val) / prior_val) * 100
                sign = "+" if pct >= 0 else ""
                change = f"{sign}{pct:.1f}%"
            rows_data.append({
                "value": row["value"],
                "current": current_val,
                "prior": prior_val,
                "change": change,
            })

        header = f"{dimension_label} comparison: {metric_display} ({current_display} vs {prior_display}):"
        lines = [header, "", f"{dimension_label} | Current | Prior | Change"]
        for r in rows_data:
            display_val = r["value"][:35] if len(r["value"]) > 35 else r["value"]
            lines.append(f"{display_val:35} | {r['current']:>7,.0f} | {r['prior']:>6,.0f} | {r['change']}")

        return {
            "status": "success",
            "message": "\n".join(lines),
            "data": {
                "rows": rows_data,
                "current_period": current_display,
                "prior_period": prior_display,
                "dimension": dimension_label,
                "metric": metric_display,
            },
        }

    except ValueError as e:
        return {"status": "error", "message": f"Invalid parameter: {e}", "data": {}}
    except AdobeAnalyticsError as e:
        return {"status": "error", "message": f"Adobe Analytics error: {e}", "data": {}}
    except Exception:
        logger.exception("Unhandled error in compare_query")
        return {"status": "error", "message": "An unexpected error occurred. Please try again.", "data": {}}
