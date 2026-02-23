"""Opal tool manifest for Adobe Analytics connector."""


def get_manifest(base_url: str) -> dict:
    """Return the full tool manifest for Opal discovery.

    Opal calls GET /discovery when registering or syncing the tool.
    The manifest describes all available tools, their parameters, and invocation URLs.

    Args:
        base_url: The deployed service URL (e.g. https://your-app.up.railway.app).

    Returns:
        Manifest dict with schema_version and tools array.
    """
    base_url = base_url.rstrip("/")
    return {
        "schema_version": "v1",
        "tools": [
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
                "invocation": {
                    "url": f"{base_url}/tools/traffic",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                },
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
                "invocation": {
                    "url": f"{base_url}/tools/referrers",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                },
            },
        ],
    }
