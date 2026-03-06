"""Shared builder for structured clarification responses."""

from typing import Any, Optional


def build_clarification(
    clarification_type: str,
    message: str,
    input_value: str,
    options: Optional[list[dict]] = None,
) -> dict[str, Any]:
    """Build a structured clarification response.

    Args:
        clarification_type: One of "ambiguous_dimension", "ambiguous_metric",
            "ambiguous_segment", "unrecognized_dimension", "unrecognized_metric",
            "unrecognized_segment", "invalid_date_range".
        message: Human-readable explanation.
        input_value: The original input that couldn't be resolved.
        options: List of suggestion dicts [{"id": ..., "name": ..., "score": ...}].

    Returns:
        Dict with status="clarification_needed" and structured data.
    """
    return {
        "status": "clarification_needed",
        "message": message,
        "data": {
            "clarification_type": clarification_type,
            "input": input_value,
            "options": options or [],
        },
    }


def build_dimension_clarification(
    input_value: str,
    suggestions: list[dict],
    ambiguous: bool = True,
) -> dict[str, Any]:
    """Build clarification for an ambiguous or unrecognized dimension."""
    ctype = "ambiguous_dimension" if ambiguous else "unrecognized_dimension"
    msg = (
        f"Multiple dimensions match '{input_value}'. Please specify which one."
        if ambiguous
        else f"Unknown dimension: '{input_value}'. Did you mean one of these?"
    )
    return build_clarification(ctype, msg, input_value, suggestions)


def build_metric_clarification(
    input_value: str,
    suggestions: list[dict],
    ambiguous: bool = True,
) -> dict[str, Any]:
    """Build clarification for an ambiguous or unrecognized metric."""
    ctype = "ambiguous_metric" if ambiguous else "unrecognized_metric"
    msg = (
        f"Multiple metrics match '{input_value}'. Please specify which one."
        if ambiguous
        else f"Unknown metric: '{input_value}'. Did you mean one of these?"
    )
    return build_clarification(ctype, msg, input_value, suggestions)


def build_segment_clarification(
    input_value: str,
    suggestions: list[dict],
    ambiguous: bool = True,
) -> dict[str, Any]:
    """Build clarification for an ambiguous or unrecognized segment."""
    ctype = "ambiguous_segment" if ambiguous else "unrecognized_segment"
    msg = (
        f"Multiple segments match '{input_value}'. Please specify which one."
        if ambiguous
        else f"Unknown segment: '{input_value}'. Did you mean one of these?"
    )
    return build_clarification(ctype, msg, input_value, suggestions)


def build_date_range_clarification(
    input_value: str,
    fallback_display: str,
) -> dict[str, Any]:
    """Build clarification for an unrecognized date range."""
    return build_clarification(
        "invalid_date_range",
        f"Could not parse date range '{input_value}'. Defaulting to {fallback_display}.",
        input_value,
    )
