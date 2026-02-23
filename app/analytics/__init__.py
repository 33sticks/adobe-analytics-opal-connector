"""Adobe Analytics API client and related utilities."""

from app.analytics.client import AdobeAnalyticsClient, AdobeAnalyticsError, get_analytics_client
from app.analytics.query_builder import (
    DIMENSION_MAP,
    METRIC_MAP,
    build_ranked_report,
    build_trended_report,
    resolve_dimension,
    resolve_metric,
)
from app.analytics.response_parser import (
    DIMENSION_DISPLAY,
    METRIC_DISPLAY,
    AnalyticsResult,
    parse_report_response,
    parse_segments_response,
)

__all__ = [
    "AdobeAnalyticsClient",
    "AdobeAnalyticsError",
    "AnalyticsResult",
    "DIMENSION_DISPLAY",
    "DIMENSION_MAP",
    "METRIC_DISPLAY",
    "METRIC_MAP",
    "build_ranked_report",
    "build_trended_report",
    "get_analytics_client",
    "parse_report_response",
    "parse_segments_response",
    "resolve_dimension",
    "resolve_metric",
]
