"""
Transforms Adobe Analytics API responses into clean, structured data for the tool layer.
"""

import html
from dataclasses import dataclass
from typing import Any, Union

from app.metadata.registry import get_registry

# Legacy display maps — kept for backward compatibility
DIMENSION_DISPLAY: dict[str, str] = {
    "variables/page": "Page",
    "variables/referrertype": "Referrer Type",
    "variables/daterangeday": "Date",
}

METRIC_DISPLAY: dict[str, str] = {
    "metrics/pageviews": "Page Views",
    "metrics/occurrences": "Occurrences",
}


def get_dimension_display(adobe_id: str) -> str:
    """Get display name for a dimension ID. Checks registry first, then legacy map."""
    registry = get_registry()
    if registry.is_loaded:
        name = registry.get_dimension_display(adobe_id)
        if name:
            return name
    return DIMENSION_DISPLAY.get(adobe_id, adobe_id)


def get_metric_display(adobe_id: str) -> str:
    """Get display name for a metric ID. Checks registry first, then legacy map."""
    registry = get_registry()
    if registry.is_loaded:
        name = registry.get_metric_display(adobe_id)
        if name:
            return name
    return METRIC_DISPLAY.get(adobe_id, adobe_id)


@dataclass
class AnalyticsResult:
    """
    Structured result from parsing an Adobe Analytics report response.

    Attributes:
        rows: List of row dicts, each with "value" (dimension) and metric labels as keys.
        totals: Dict mapping metric labels to grand totals.
        date_range_display: Human-readable date range (e.g., "Feb 1–15, 2026").
        dimension_name: Display name for the dimension (e.g., "Page").
        metric_names: Display names for the metrics (e.g., ["Page Views"]).
        row_count: Number of rows returned in this response.
        total_available: totalElements from Adobe (total unique dimension values).
    """

    rows: list[dict[str, Any]]
    totals: dict[str, float]
    date_range_display: str
    dimension_name: str
    metric_names: list[str]
    row_count: int
    total_available: int


def parse_report_response(
    response: dict[str, Any],
    metric_labels: list[str],
    dimension_label: str,
    date_range_display: str,
) -> AnalyticsResult:
    """
    Parse an Adobe Analytics report response into a structured AnalyticsResult.

    Args:
        response: Raw JSON response from Adobe Reports API.
        metric_labels: Friendly names for metrics, in same order as response columns.
        dimension_label: Friendly name for the dimension (e.g., "Page").
        date_range_display: Human-readable date range from format_date_range_display().

    Returns:
        AnalyticsResult with decoded rows, totals, and metadata.
    """
    raw_rows = response.get("rows") or []
    totals_raw = response.get("summaryData") or {}
    totals_list = totals_raw.get("totals") or []
    total_elements = response.get("totalElements", 0)

    parsed_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        value_raw = row.get("value") or ""
        decoded_value = html.unescape(str(value_raw))
        data = row.get("data")
        if data is None:
            data = []
        if not isinstance(data, list):
            data = []

        row_dict: dict[str, Any] = {"value": decoded_value}
        for i, label in enumerate(metric_labels):
            row_dict[label] = data[i] if i < len(data) else 0.0
        parsed_rows.append(row_dict)

    totals_dict: dict[str, float] = {}
    for i, label in enumerate(metric_labels):
        totals_dict[label] = totals_list[i] if i < len(totals_list) else 0.0

    return AnalyticsResult(
        rows=parsed_rows,
        totals=totals_dict,
        date_range_display=date_range_display,
        dimension_name=dimension_label,
        metric_names=metric_labels,
        row_count=len(parsed_rows),
        total_available=int(total_elements),
    )


def parse_segments_response(response: Union[dict[str, Any], list[Any]]) -> list[dict[str, str]]:
    """
    Parse an Adobe Analytics segments response into a list of segment dicts.

    Handles both {"content": [...]} and direct list response formats.

    Args:
        response: Raw JSON from Adobe Segments API (dict or list).

    Returns:
        List of {"id": str, "name": str, "description": str} for each segment.
    """
    segments: list[Any] = []
    if isinstance(response, list):
        segments = response
    elif isinstance(response, dict) and "content" in response:
        content = response["content"]
        segments = content if isinstance(content, list) else []

    result: list[dict[str, str]] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        result.append(
            {
                "id": str(seg.get("id", "")),
                "name": str(seg.get("name", "")),
                "description": str(seg.get("description", "")),
            }
        )
    return result
