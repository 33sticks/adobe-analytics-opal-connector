"""Opal tool endpoints and shared utilities."""


def extract_parameters(body: dict) -> dict:
    """Extract tool parameters from Opal request body.

    Handles both nested (body["parameters"]) and flat (body["metric"]) formats.
    Applies defaults and coerces types (e.g. top_n string to int).

    Args:
        body: The raw request body from Opal.

    Returns:
        Dict with keys: metric, date_range, top_n, page_filter.
    """
    source = body.get("parameters") if isinstance(body.get("parameters"), dict) else body
    source = source or {}

    top_n = source.get("top_n", 10)
    if isinstance(top_n, str):
        try:
            top_n = int(top_n)
        except (ValueError, TypeError):
            top_n = 10

    return {
        "metric": source.get("metric", "pageviews"),
        "date_range": source.get("date_range", "last 7 days"),
        "top_n": top_n,
        "page_filter": source.get("page_filter"),
    }
