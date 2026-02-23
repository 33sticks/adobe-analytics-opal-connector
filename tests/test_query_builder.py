"""
Tests for app.analytics.query_builder.

Covers resolve_dimension, resolve_metric, build_ranked_report, and build_trended_report.
"""

import pytest

from app.analytics.query_builder import (
    build_ranked_report,
    build_trended_report,
    build_trended_report_for_page,
    resolve_dimension,
    resolve_metric,
)

SAMPLE_DATE_RANGE = "2026-02-01T00:00:00.000/2026-02-15T00:00:00.000"
SAMPLE_RSID = "33sticksjennwebprops"


class TestResolveDimension:
    """Tests for resolve_dimension()."""

    def test_known_name_page(self):
        assert resolve_dimension("page") == "variables/page"

    def test_known_name_referrer_type(self):
        assert resolve_dimension("referrer_type") == "variables/referrertype"

    def test_known_name_referrertype(self):
        assert resolve_dimension("referrertype") == "variables/referrertype"

    def test_known_name_date(self):
        assert resolve_dimension("date") == "variables/daterangeday"

    def test_known_name_day(self):
        assert resolve_dimension("day") == "variables/daterangeday"

    def test_case_insensitive(self):
        assert resolve_dimension("PAGE") == "variables/page"
        assert resolve_dimension("Referrer_Type") == "variables/referrertype"

    def test_adobe_format_passthrough(self):
        assert resolve_dimension("variables/page") == "variables/page"
        assert resolve_dimension("variables/referrertype") == "variables/referrertype"
        assert resolve_dimension("variables/daterangeday") == "variables/daterangeday"

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown dimension"):
            resolve_dimension("unknown_dimension")

    def test_empty_raises_value_error(self):
        with pytest.raises(ValueError):
            resolve_dimension("")


class TestResolveMetric:
    """Tests for resolve_metric()."""

    def test_known_name_pageviews(self):
        assert resolve_metric("pageviews") == "metrics/pageviews"

    def test_known_name_page_views(self):
        assert resolve_metric("page_views") == "metrics/pageviews"

    def test_known_name_occurrences(self):
        assert resolve_metric("occurrences") == "metrics/occurrences"

    def test_case_insensitive(self):
        assert resolve_metric("PAGEVIEWS") == "metrics/pageviews"
        assert resolve_metric("Page_Views") == "metrics/pageviews"

    def test_adobe_format_passthrough(self):
        assert resolve_metric("metrics/pageviews") == "metrics/pageviews"
        assert resolve_metric("metrics/occurrences") == "metrics/occurrences"

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown metric"):
            resolve_metric("unknown_metric")

    def test_empty_raises_value_error(self):
        with pytest.raises(ValueError):
            resolve_metric("")


class TestBuildRankedReport:
    """Tests for build_ranked_report()."""

    def test_minimal_call(self):
        """Minimal call with required params only."""
        result = build_ranked_report(
            rsid=SAMPLE_RSID,
            dimension="page",
            metrics=["pageviews"],
            date_range=SAMPLE_DATE_RANGE,
        )
        assert result["rsid"] == SAMPLE_RSID
        assert result["dimension"] == "variables/page"
        assert result["metricContainer"]["metrics"] == [
            {"columnId": "0", "id": "metrics/pageviews"}
        ]
        assert result["globalFilters"] == [
            {"type": "dateRange", "dateRange": SAMPLE_DATE_RANGE}
        ]
        assert result["settings"] == {
            "countRepeatInstances": True,
            "limit": 10,
            "page": 0,
            "nonesBehavior": "return-nones",
        }
        assert "search" not in result

    def test_with_search_filter(self):
        """Search filter adds search.clause."""
        result = build_ranked_report(
            rsid=SAMPLE_RSID,
            dimension="page",
            metrics=["pageviews"],
            date_range=SAMPLE_DATE_RANGE,
            search_filter="/products",
        )
        assert result["search"] == {"clause": "( CONTAINS '/products' )"}

    def test_with_segment_id(self):
        """Segment ID adds segment to globalFilters."""
        result = build_ranked_report(
            rsid=SAMPLE_RSID,
            dimension="page",
            metrics=["pageviews"],
            date_range=SAMPLE_DATE_RANGE,
            segment_id="s123_abc",
        )
        assert result["globalFilters"] == [
            {"type": "dateRange", "dateRange": SAMPLE_DATE_RANGE},
            {"type": "segment", "segmentId": "s123_abc"},
        ]

    def test_multiple_metrics(self):
        """Multiple metrics get sequential columnIds."""
        result = build_ranked_report(
            rsid=SAMPLE_RSID,
            dimension="page",
            metrics=["pageviews", "occurrences"],
            date_range=SAMPLE_DATE_RANGE,
        )
        assert result["metricContainer"]["metrics"] == [
            {"columnId": "0", "id": "metrics/pageviews"},
            {"columnId": "1", "id": "metrics/occurrences"},
        ]

    def test_custom_limit_and_page(self):
        """Custom limit and page in settings."""
        result = build_ranked_report(
            rsid=SAMPLE_RSID,
            dimension="page",
            metrics=["pageviews"],
            date_range=SAMPLE_DATE_RANGE,
            limit=25,
            page=2,
        )
        assert result["settings"]["limit"] == 25
        assert result["settings"]["page"] == 2

    def test_search_filter_and_segment_together(self):
        """Both search_filter and segment_id can be applied."""
        result = build_ranked_report(
            rsid=SAMPLE_RSID,
            dimension="page",
            metrics=["pageviews"],
            date_range=SAMPLE_DATE_RANGE,
            search_filter="/home",
            segment_id="s456_def",
        )
        assert result["search"] == {"clause": "( CONTAINS '/home' )"}
        assert len(result["globalFilters"]) == 2
        assert result["globalFilters"][1] == {"type": "segment", "segmentId": "s456_def"}


class TestBuildTrendedReport:
    """Tests for build_trended_report()."""

    def test_correct_structure(self):
        """Returns valid report structure with date dimension."""
        result = build_trended_report(
            rsid=SAMPLE_RSID,
            metric="pageviews",
            date_range=SAMPLE_DATE_RANGE,
        )
        assert result["rsid"] == SAMPLE_RSID
        assert result["dimension"] == "variables/daterangeday"
        assert result["metricContainer"]["metrics"] == [
            {"columnId": "0", "id": "metrics/pageviews"}
        ]
        assert result["globalFilters"] == [
            {"type": "dateRange", "dateRange": SAMPLE_DATE_RANGE}
        ]

    def test_dimension_fixed_to_daterangeday(self):
        """Dimension is always variables/daterangeday regardless of metric."""
        result = build_trended_report(
            rsid=SAMPLE_RSID,
            metric="occurrences",
            date_range=SAMPLE_DATE_RANGE,
        )
        assert result["dimension"] == "variables/daterangeday"

    def test_limit_400(self):
        """Limit is 400 for trended reports (daily data)."""
        result = build_trended_report(
            rsid=SAMPLE_RSID,
            metric="pageviews",
            date_range=SAMPLE_DATE_RANGE,
        )
        assert result["settings"]["limit"] == 400

    def test_with_search_filter(self):
        """Search filter is passed through."""
        result = build_trended_report(
            rsid=SAMPLE_RSID,
            metric="pageviews",
            date_range=SAMPLE_DATE_RANGE,
            search_filter="/pricing",
        )
        assert result["search"] == {"clause": "( CONTAINS '/pricing' )"}

    def test_with_segment_id(self):
        """Segment ID is passed through."""
        result = build_trended_report(
            rsid=SAMPLE_RSID,
            metric="pageviews",
            date_range=SAMPLE_DATE_RANGE,
            segment_id="s789_ghi",
        )
        assert result["globalFilters"] == [
            {"type": "dateRange", "dateRange": SAMPLE_DATE_RANGE},
            {"type": "segment", "segmentId": "s789_ghi"},
        ]


class TestBuildTrendedReportForPage:
    """Tests for build_trended_report_for_page()."""

    def test_correct_structure(self):
        """Returns valid report structure with metricFilters and page itemId."""
        result = build_trended_report_for_page(
            rsid=SAMPLE_RSID,
            metric="pageviews",
            date_range=SAMPLE_DATE_RANGE,
            page_item_id="2439908651",
        )
        assert result["rsid"] == SAMPLE_RSID
        assert result["dimension"] == "variables/daterangeday"
        assert result["metricContainer"]["metrics"] == [
            {"columnId": "0", "id": "metrics/pageviews", "filters": ["page_filter_0"]}
        ]
        assert result["metricContainer"]["metricFilters"] == [
            {
                "id": "page_filter_0",
                "type": "breakdown",
                "dimension": "variables/page",
                "itemId": "2439908651",
            }
        ]
        assert result["globalFilters"] == [
            {"type": "dateRange", "dateRange": SAMPLE_DATE_RANGE}
        ]
        assert result["settings"]["limit"] == 400

    def test_custom_dimension_id(self):
        """Custom dimension_id is passed."""
        result = build_trended_report_for_page(
            rsid=SAMPLE_RSID,
            metric="occurrences",
            date_range=SAMPLE_DATE_RANGE,
            page_item_id="123",
            dimension_id="variables/custompage",
        )
        assert result["metricContainer"]["metricFilters"][0]["dimension"] == "variables/custompage"
