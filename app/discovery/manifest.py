"""Opal tool manifest for Adobe Analytics connector."""

import logging

from app.metadata.registry import get_registry

logger = logging.getLogger(__name__)


def _build_dynamic_description() -> dict:
    """Build dynamic descriptions with actual available names from the registry."""
    registry = get_registry()
    if not registry.is_loaded:
        return {"dimensions": "", "metrics": "", "segments": ""}

    dims = registry.list_dimensions()[:20]
    mets = registry.list_metrics()[:15]
    segs = registry.list_segments()[:15]

    dim_names = ", ".join(d["name"] for d in dims)
    met_names = ", ".join(m["name"] for m in mets)
    seg_names = ", ".join(s["name"] for s in segs)

    return {
        "dimensions": dim_names,
        "metrics": met_names,
        "segments": seg_names,
    }


def get_manifest() -> dict:
    """Return the full tool manifest for Opal discovery.

    Opal calls GET /discovery when registering or syncing the tool.
    The manifest describes all available tools, their parameters, and invocation paths.

    Returns:
        Manifest dict with functions array.
    """
    avail = _build_dynamic_description()

    # Build dynamic descriptions for new tools
    query_desc = (
        "Runs a flexible Adobe Analytics query with any dimension, metric(s), segment, "
        "date range, and filter. Use this as the primary tool for any analytics question "
        "that doesn't fit the specialized tools. Supports fuzzy matching of names."
    )
    if avail["dimensions"]:
        query_desc += f" Available dimensions include: {avail['dimensions']}."
    if avail["metrics"]:
        query_desc += f" Available metrics include: {avail['metrics']}."
    if avail["segments"]:
        query_desc += f" Available segments include: {avail['segments']}."

    trend_desc = (
        "Returns a time-series trend for any Adobe Analytics metric, broken down by day, "
        "week, or month. Use this when users ask about trends over time, daily/weekly/monthly "
        "patterns, or time-series analysis."
    )
    if avail["metrics"]:
        trend_desc += f" Available metrics include: {avail['metrics']}."

    compare_desc = (
        "Compares any Adobe Analytics dimension/metric across two time periods. "
        "Use this for period-over-period analysis, performance changes, or before/after comparisons. "
        "Automatically calculates the prior period if not specified."
    )
    if avail["dimensions"]:
        compare_desc += f" Available dimensions include: {avail['dimensions']}."

    schema_desc = (
        "Lists all available Adobe Analytics dimensions, metrics, and segments. "
        "Use this when users ask 'what can I query?', 'what dimensions are available?', "
        "or need to discover what data is accessible. Supports filtering by category and search."
    )

    return {
        "functions": [
            # --- Existing specialized tools (backward compatible) ---
            {
                "name": "adobe_analytics_traffic",
                "description": "Retrieves page-level traffic data from Adobe Analytics. Use this when users ask about page views, top pages, traffic trends, or website performance over a time period. Available metrics: pageviews, occurrences. Can filter by page name and limit results to top N pages.",
                "parameters": [
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "The metric to retrieve. Options: 'pageviews' or 'occurrences'. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "date_range",
                        "type": "string",
                        "description": "The time period to analyze, in natural language. Examples: 'last 7 days', 'last week', 'this month', 'last 30 days'. Default: 'last 7 days'.",
                        "required": False,
                    },
                    {
                        "name": "top_n",
                        "type": "integer",
                        "description": "Number of top pages to return, ranked by the selected metric. Default: 10. Max: 50.",
                        "required": False,
                    },
                    {
                        "name": "page_filter",
                        "type": "string",
                        "description": "Optional filter to limit results to pages containing this string. Example: '/products' would match '/products', '/products/shoes', etc.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/traffic",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_referrers",
                "description": "Breaks down website traffic by referrer type from Adobe Analytics. Use this when users ask where their traffic is coming from, about traffic sources, or referral analysis. Shows breakdown by Direct, Organic Search, Paid Search, Social, and Referring Domains.",
                "parameters": [
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "The metric to retrieve. Options: 'pageviews' or 'occurrences'. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "date_range",
                        "type": "string",
                        "description": "The time period to analyze, in natural language. Examples: 'last 7 days', 'last week', 'this month', 'last 30 days'. Default: 'last 7 days'.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/referrers",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_page_comparison",
                "description": "Compares page performance across two time periods in Adobe Analytics. Use this when users ask to compare pages, want period-over-period analysis, or ask about traffic changes over time. Shows absolute numbers and percent change for each page.",
                "parameters": [
                    {
                        "name": "pages",
                        "type": "string",
                        "description": "Comma-separated list of page names to compare. Example: '/home, /about, /contact'",
                        "required": True,
                    },
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "'pageviews' or 'occurrences'. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "current_period",
                        "type": "string",
                        "description": "The current time period in natural language. Default: 'last 7 days'.",
                        "required": False,
                    },
                    {
                        "name": "prior_period",
                        "type": "string",
                        "description": "The comparison time period in natural language. Default: 'last 14 days' offset to the period before current_period. If not specified, automatically uses the same-length period immediately before current_period.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/compare",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_segments",
                "description": "Breaks down website traffic by audience segment from Adobe Analytics. Use this when users ask about mobile vs desktop traffic, new vs returning visitors, or any segment-level comparison. Available segments include Mobile Visitors, Desktop Visitors, Tablet Visitors, New Visitors, and Return Visitors.",
                "parameters": [
                    {
                        "name": "segments",
                        "type": "string",
                        "description": "Comma-separated segment names to compare. Available: 'mobile', 'desktop', 'phones', 'tablet', 'new visitors', 'return visitors', 'search', 'social', 'single page visits', 'non-bounces'.",
                        "required": True,
                    },
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "'pageviews' or 'occurrences'. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "date_range",
                        "type": "string",
                        "description": "Time period in natural language. Default: 'last 7 days'.",
                        "required": False,
                    },
                    {
                        "name": "dimension",
                        "type": "string",
                        "description": "'page' or 'referrer_type'. Default: 'page'. Determines the breakdown dimension.",
                        "required": False,
                    },
                    {
                        "name": "top_n",
                        "type": "integer",
                        "description": "Number of top items to return per segment. Default: 5. Max: 20.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/segments",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_traffic_validation",
                "description": "Analyzes daily traffic patterns for a specific page to help validate if there is enough traffic for an A/B test. Use this when users ask about traffic volume for experiment planning, want to know if a page gets enough traffic for testing, or need daily traffic trends. Provides daily averages, min/max, trend direction, and estimated sample size for a given test duration.",
                "parameters": [
                    {
                        "name": "page_filter",
                        "type": "string",
                        "description": "Page name or partial match to analyze. Example: '/pricing' or 'homepage'.",
                        "required": True,
                    },
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "'pageviews' or 'occurrences'. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "date_range",
                        "type": "string",
                        "description": "Time period to analyze. Default: 'last 30 days'. Longer periods give more reliable estimates.",
                        "required": False,
                    },
                    {
                        "name": "test_duration_days",
                        "type": "integer",
                        "description": "Planned test duration in days. Default: 14. Used to estimate total traffic during the test.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/validation",
                "http_method": "POST",
                "auth_requirements": [],
            },
            # --- New general-purpose tools ---
            {
                "name": "adobe_analytics_query",
                "description": query_desc,
                "parameters": [
                    {
                        "name": "dimension",
                        "type": "string",
                        "description": "The dimension to break down by (e.g. 'page', 'browser', 'country', 'entry page'). Supports fuzzy matching. Default: 'page'.",
                        "required": False,
                    },
                    {
                        "name": "metrics",
                        "type": "string",
                        "description": "Comma-separated metrics to retrieve (e.g. 'pageviews', 'visits, visitors'). Supports fuzzy matching. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "segment",
                        "type": "string",
                        "description": "Optional segment to apply (e.g. 'mobile', 'new visitors'). Supports fuzzy matching.",
                        "required": False,
                    },
                    {
                        "name": "date_range",
                        "type": "string",
                        "description": "Time period in natural language. Default: 'last 7 days'.",
                        "required": False,
                    },
                    {
                        "name": "filter",
                        "type": "string",
                        "description": "Optional filter for dimension values (CONTAINS match).",
                        "required": False,
                    },
                    {
                        "name": "top_n",
                        "type": "integer",
                        "description": "Number of results to return. Default: 10. Max: 50.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/query",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_trend",
                "description": trend_desc,
                "parameters": [
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "The metric to trend (e.g. 'pageviews', 'visits', 'bounce rate'). Supports fuzzy matching. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "date_range",
                        "type": "string",
                        "description": "Time period in natural language. Default: 'last 30 days'.",
                        "required": False,
                    },
                    {
                        "name": "granularity",
                        "type": "string",
                        "description": "Time granularity: 'day', 'week', or 'month'. Default: 'day'.",
                        "required": False,
                    },
                    {
                        "name": "segment",
                        "type": "string",
                        "description": "Optional segment to apply. Supports fuzzy matching.",
                        "required": False,
                    },
                    {
                        "name": "filter",
                        "type": "string",
                        "description": "Optional filter for dimension values.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/query/trend",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_compare",
                "description": compare_desc,
                "parameters": [
                    {
                        "name": "dimension",
                        "type": "string",
                        "description": "Dimension to compare (e.g. 'page', 'browser'). Default: 'page'.",
                        "required": False,
                    },
                    {
                        "name": "metric",
                        "type": "string",
                        "description": "Metric to compare. Default: 'pageviews'.",
                        "required": False,
                    },
                    {
                        "name": "current_period",
                        "type": "string",
                        "description": "Current time period in natural language. Default: 'last 7 days'.",
                        "required": False,
                    },
                    {
                        "name": "prior_period",
                        "type": "string",
                        "description": "Prior time period. Auto-calculated if not specified.",
                        "required": False,
                    },
                    {
                        "name": "segment",
                        "type": "string",
                        "description": "Optional segment to apply.",
                        "required": False,
                    },
                    {
                        "name": "filter",
                        "type": "string",
                        "description": "Optional filter for dimension values.",
                        "required": False,
                    },
                    {
                        "name": "top_n",
                        "type": "integer",
                        "description": "Number of results to compare. Default: 10.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/query/compare",
                "http_method": "POST",
                "auth_requirements": [],
            },
            {
                "name": "adobe_analytics_schema",
                "description": schema_desc,
                "parameters": [
                    {
                        "name": "category",
                        "type": "string",
                        "description": "Filter by category: 'dimensions', 'metrics', 'segments', or 'all'. Default: 'all'.",
                        "required": False,
                    },
                    {
                        "name": "search",
                        "type": "string",
                        "description": "Optional search string to filter results by name.",
                        "required": False,
                    },
                ],
                "endpoint": "/tools/schema",
                "http_method": "POST",
                "auth_requirements": [],
            },
        ],
    }
