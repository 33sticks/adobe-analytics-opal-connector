"""Opal tool manifest for Adobe Analytics connector."""


def get_manifest() -> dict:
    """Return the full tool manifest for Opal discovery.

    Opal calls GET /discovery when registering or syncing the tool.
    The manifest describes all available tools, their parameters, and invocation paths.

    Returns:
        Manifest dict with functions array.
    """
    return {
        "functions": [
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
        ],
    }
