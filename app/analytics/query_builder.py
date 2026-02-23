"""
Builds Adobe Analytics 2.0 API request bodies from tool parameters.

Pure functions only — no side effects.
"""

from typing import Optional

DIMENSION_MAP = {
    "page": "variables/page",
    "referrer_type": "variables/referrertype",
    "referrertype": "variables/referrertype",
    "date": "variables/daterangeday",
    "day": "variables/daterangeday",
}

METRIC_MAP = {
    "pageviews": "metrics/pageviews",
    "page_views": "metrics/pageviews",
    "occurrences": "metrics/occurrences",
}


def resolve_dimension(name: str) -> str:
    """
    Resolve a dimension name to its Adobe Analytics API ID.

    Args:
        name: Human-friendly name (e.g. "page", "referrer_type") or
              Adobe format (e.g. "variables/page").

    Returns:
        Adobe dimension ID (e.g. "variables/page").

    Raises:
        ValueError: If the dimension is unknown.
    """
    normalized = name.strip().lower()
    if name.startswith("variables/"):
        return name
    if normalized in DIMENSION_MAP:
        return DIMENSION_MAP[normalized]
    raise ValueError(f"Unknown dimension: {name!r}")


def resolve_metric(name: str) -> str:
    """
    Resolve a metric name to its Adobe Analytics API ID.

    Args:
        name: Human-friendly name (e.g. "pageviews", "occurrences") or
              Adobe format (e.g. "metrics/pageviews").

    Returns:
        Adobe metric ID (e.g. "metrics/pageviews").

    Raises:
        ValueError: If the metric is unknown.
    """
    normalized = name.strip().lower()
    if name.startswith("metrics/"):
        return name
    if normalized in METRIC_MAP:
        return METRIC_MAP[normalized]
    raise ValueError(f"Unknown metric: {name!r}")


def build_ranked_report(
    rsid: str,
    dimension: str,
    metrics: list[str],
    date_range: str,
    limit: int = 10,
    page: int = 0,
    search_filter: Optional[str] = None,
    segment_id: Optional[str] = None,
) -> dict:
    """
    Build an Adobe Analytics ranked report request body.

    Args:
        rsid: Report suite ID.
        dimension: Dimension to break down by (resolved via resolve_dimension).
        metrics: List of metrics (resolved via resolve_metric).
        date_range: Date range in Adobe ISO format
            (YYYY-MM-DDTHH:MM:SS.000/YYYY-MM-DDTHH:MM:SS.000).
        limit: Maximum number of rows to return. Default 10.
        page: Page number for pagination. Default 0.
        search_filter: Optional filter for dimension values (CONTAINS clause).
        segment_id: Optional segment ID to apply.

    Returns:
        Dict matching the Adobe Analytics Reports API request body format.
    """
    resolved_dimension = resolve_dimension(dimension)
    resolved_metrics = [resolve_metric(m) for m in metrics]

    global_filters: list[dict] = [
        {"type": "dateRange", "dateRange": date_range},
    ]
    if segment_id:
        global_filters.append({"type": "segment", "segmentId": segment_id})

    metric_container = {
        "metrics": [
            {"columnId": str(i), "id": mid}
            for i, mid in enumerate(resolved_metrics)
        ]
    }

    settings = {
        "countRepeatInstances": True,
        "limit": limit,
        "page": page,
        "nonesBehavior": "return-nones",
    }

    body: dict = {
        "rsid": rsid,
        "globalFilters": global_filters,
        "metricContainer": metric_container,
        "dimension": resolved_dimension,
        "settings": settings,
    }

    if search_filter:
        body["search"] = {"clause": f"( CONTAINS '{search_filter}' )"}

    return body


def build_trended_report(
    rsid: str,
    metric: str,
    date_range: str,
    search_filter: Optional[str] = None,
    segment_id: Optional[str] = None,
) -> dict:
    """
    Build an Adobe Analytics trended report request body (daily granularity).

    Dimension is always variables/daterangeday. Limit is 400 to accommodate
    daily data over long ranges.

    Args:
        rsid: Report suite ID.
        metric: Metric to trend (resolved via resolve_metric).
        date_range: Date range in Adobe ISO format.
        search_filter: Optional filter for dimension values.
        segment_id: Optional segment ID to apply.

    Returns:
        Dict matching the Adobe Analytics Reports API request body format.
    """
    return build_ranked_report(
        rsid=rsid,
        dimension="variables/daterangeday",
        metrics=[metric],
        date_range=date_range,
        limit=400,
        page=0,
        search_filter=search_filter,
        segment_id=segment_id,
    )
