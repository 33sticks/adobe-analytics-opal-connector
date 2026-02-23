"""
Tests for app.analytics.response_parser.

Covers parse_report_response, parse_segments_response, and display name constants.
"""

import pytest

from app.analytics.response_parser import (
    DIMENSION_DISPLAY,
    METRIC_DISPLAY,
    AnalyticsResult,
    parse_report_response,
    parse_segments_response,
)


# Sample Adobe report response (from PROJECT_SPEC / sandbox)
SAMPLE_REPORT_RESPONSE = {
    "totalPages": 16,
    "firstPage": True,
    "lastPage": False,
    "numberOfElements": 5,
    "number": 0,
    "totalElements": 80,
    "rows": [
        {"data": [3352.0], "itemId": "2439908651", "value": "beacon parser > beacon parsed successfully"},
        {"data": [983.0], "itemId": "2437100290", "value": "beacon parser > main"},
        {"data": [119.0], "itemId": "3568101380", "value": "DDT Blog > post > how i got onetrust to work with adobe launch"},
        {"data": [101.0], "itemId": "3324792768", "value": "DDT Blog > homepage >"},
        {
            "data": [35.0],
            "itemId": "3865949280",
            "value": "DDT Blog > post > problems with the &#8220;autoblock&#8221; approach to consent management",
        },
    ],
    "summaryData": {
        "filteredTotals": [4832.0],
        "totals": [4832.0],
    },
}


class TestParseReportResponse:
    """Tests for parse_report_response()."""

    def test_normal_case_single_metric(self):
        """Parse standard report with one metric."""
        result = parse_report_response(
            SAMPLE_REPORT_RESPONSE,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert isinstance(result, AnalyticsResult)
        assert result.row_count == 5
        assert result.total_available == 80
        assert result.dimension_name == "Page"
        assert result.metric_names == ["Page Views"]
        assert result.date_range_display == "Feb 1–15, 2026"
        assert result.totals == {"Page Views": 4832.0}

        assert result.rows[0] == {"value": "beacon parser > beacon parsed successfully", "Page Views": 3352.0}
        assert result.rows[1] == {"value": "beacon parser > main", "Page Views": 983.0}

    def test_html_entity_decoding(self):
        """HTML entities in dimension values are decoded."""
        result = parse_report_response(
            SAMPLE_REPORT_RESPONSE,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        # Last row has &#8220; and &#8221; (left/right double quote) -> decoded to Unicode quotes
        last_row = result.rows[-1]
        assert "&#8220;" not in last_row["value"]
        assert "&#8221;" not in last_row["value"]
        # html.unescape produces Unicode curly quotes (U+201C, U+201D), not ASCII "
        assert "\u201c" in last_row["value"] and "\u201d" in last_row["value"]
        assert last_row["value"] == (
            "DDT Blog > post > problems with the \u201cautoblock\u201d approach to consent management"
        )

    def test_multiple_metrics(self):
        """Multiple metrics map correctly by index."""
        response = {
            "totalElements": 3,
            "rows": [
                {"data": [100.0, 50.0], "itemId": "1", "value": "page-a"},
                {"data": [200.0, 75.0], "itemId": "2", "value": "page-b"},
            ],
            "summaryData": {"totals": [300.0, 125.0]},
        }
        result = parse_report_response(
            response,
            metric_labels=["Page Views", "Occurrences"],
            dimension_label="Page",
            date_range_display="Feb 10–16, 2026",
        )
        assert result.rows[0] == {"value": "page-a", "Page Views": 100.0, "Occurrences": 50.0}
        assert result.rows[1] == {"value": "page-b", "Page Views": 200.0, "Occurrences": 75.0}
        assert result.totals == {"Page Views": 300.0, "Occurrences": 125.0}

    def test_empty_rows(self):
        """Empty rows returns valid result with zeros."""
        response = {
            "totalElements": 0,
            "rows": [],
            "summaryData": {"totals": [0.0]},
        }
        result = parse_report_response(
            response,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert result.rows == []
        assert result.row_count == 0
        assert result.total_available == 0
        assert result.totals == {"Page Views": 0.0}

    def test_missing_summary_data(self):
        """Missing summaryData yields zero totals."""
        response = {
            "totalElements": 2,
            "rows": [
                {"data": [10.0], "itemId": "1", "value": "a"},
                {"data": [20.0], "itemId": "2", "value": "b"},
            ],
        }
        result = parse_report_response(
            response,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert result.rows[0]["Page Views"] == 10.0
        assert result.rows[1]["Page Views"] == 20.0
        assert result.totals == {"Page Views": 0.0}

    def test_row_with_none_data(self):
        """Row with None data uses zeros for metrics."""
        response = {
            "totalElements": 1,
            "rows": [{"data": None, "itemId": "1", "value": "page-x"}],
            "summaryData": {"totals": [5.0]},
        }
        result = parse_report_response(
            response,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert result.rows[0] == {"value": "page-x", "Page Views": 0.0}

    def test_row_with_empty_data_array(self):
        """Row with empty data array uses zeros."""
        response = {
            "totalElements": 1,
            "rows": [{"data": [], "itemId": "1", "value": "page-y"}],
            "summaryData": {"totals": [10.0]},
        }
        result = parse_report_response(
            response,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert result.rows[0] == {"value": "page-y", "Page Views": 0.0}

    def test_row_data_shorter_than_metrics(self):
        """Row with fewer data values than metrics pads with 0.0."""
        response = {
            "totalElements": 1,
            "rows": [{"data": [100.0], "itemId": "1", "value": "page-z"}],
            "summaryData": {"totals": [100.0, 50.0]},
        }
        result = parse_report_response(
            response,
            metric_labels=["Page Views", "Occurrences"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert result.rows[0] == {"value": "page-z", "Page Views": 100.0, "Occurrences": 0.0}

    def test_missing_rows_key(self):
        """Response without 'rows' key treats as empty."""
        response = {"totalElements": 5, "summaryData": {"totals": [100.0]}}
        result = parse_report_response(
            response,
            metric_labels=["Page Views"],
            dimension_label="Page",
            date_range_display="Feb 1–15, 2026",
        )
        assert result.rows == []
        assert result.row_count == 0
        assert result.total_available == 5


class TestParseSegmentsResponse:
    """Tests for parse_segments_response()."""

    def test_content_format(self):
        """Handles {'content': [...]} format."""
        response = {
            "content": [
                {"id": "s123", "name": "Mobile Visitors", "description": "Visitors on mobile devices"},
                {"id": "s456", "name": "Desktop Visitors", "description": ""},
            ]
        }
        result = parse_segments_response(response)
        assert result == [
            {"id": "s123", "name": "Mobile Visitors", "description": "Visitors on mobile devices"},
            {"id": "s456", "name": "Desktop Visitors", "description": ""},
        ]

    def test_direct_list_format(self):
        """Handles direct list format."""
        response = [
            {"id": "s789", "name": "Return Visitors", "description": "Returning visitors"},
        ]
        result = parse_segments_response(response)
        assert result == [
            {"id": "s789", "name": "Return Visitors", "description": "Returning visitors"},
        ]

    def test_empty_content(self):
        """Empty content returns empty list."""
        assert parse_segments_response({"content": []}) == []
        assert parse_segments_response([]) == []

    def test_missing_content_key(self):
        """Dict without 'content' returns empty list."""
        assert parse_segments_response({"other": "value"}) == []

    def test_missing_segment_fields(self):
        """Missing id, name, or description uses empty string."""
        response = {"content": [{"id": "s1"}, {"name": "Only Name"}]}
        result = parse_segments_response(response)
        assert result[0] == {"id": "s1", "name": "", "description": ""}
        assert result[1] == {"id": "", "name": "Only Name", "description": ""}

    def test_skips_non_dict_items(self):
        """Non-dict items in content are skipped."""
        response = {"content": [{"id": "s1", "name": "A", "description": ""}, "invalid", None, 42]}
        result = parse_segments_response(response)
        assert result == [{"id": "s1", "name": "A", "description": ""}]


class TestDisplayConstants:
    """Tests for DIMENSION_DISPLAY and METRIC_DISPLAY."""

    def test_dimension_display_has_expected_keys(self):
        """DIMENSION_DISPLAY maps Adobe dimension IDs to display names."""
        assert DIMENSION_DISPLAY["variables/page"] == "Page"
        assert DIMENSION_DISPLAY["variables/referrertype"] == "Referrer Type"
        assert DIMENSION_DISPLAY["variables/daterangeday"] == "Date"

    def test_metric_display_has_expected_keys(self):
        """METRIC_DISPLAY maps Adobe metric IDs to display names."""
        assert METRIC_DISPLAY["metrics/pageviews"] == "Page Views"
        assert METRIC_DISPLAY["metrics/occurrences"] == "Occurrences"
