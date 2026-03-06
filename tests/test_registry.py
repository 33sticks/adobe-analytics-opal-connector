"""Tests for app.metadata.registry — MetadataRegistry + fuzzy matching."""

import pytest

from app.metadata.registry import MetadataRegistry, ResolveResult


SAMPLE_SCHEMA = {
    "dimensions": [
        {"id": "variables/page", "name": "Page", "aliases": ["page", "pagename", "page_name"]},
        {"id": "variables/referrertype", "name": "Referrer Type", "aliases": ["referrer type", "referrer_type", "referrertype", "traffic source"]},
        {"id": "variables/daterangeday", "name": "Day", "aliases": ["day", "date", "daterangeday"]},
        {"id": "variables/browser", "name": "Browser", "aliases": ["browser", "browsers"]},
        {"id": "variables/entrypage", "name": "Entry Page", "aliases": ["entry page", "entry_page", "entrypage", "landing page"]},
        {"id": "variables/geocountry", "name": "Country", "aliases": ["country", "geocountry"]},
        {"id": "variables/georegion", "name": "Region", "aliases": ["region", "georegion", "state"]},
    ],
    "metrics": [
        {"id": "metrics/pageviews", "name": "Page Views", "aliases": ["page views", "page_views", "pageviews", "views"]},
        {"id": "metrics/visits", "name": "Visits", "aliases": ["visits", "sessions"]},
        {"id": "metrics/visitors", "name": "Unique Visitors", "aliases": ["unique visitors", "unique_visitors", "visitors", "users"]},
        {"id": "metrics/occurrences", "name": "Occurrences", "aliases": ["occurrences", "hits"]},
        {"id": "metrics/bouncerate", "name": "Bounce Rate", "aliases": ["bounce rate", "bounce_rate", "bouncerate"]},
    ],
    "segments": [
        {"id": "Visits_from_Mobile_Devices", "name": "Mobile Visitors", "aliases": ["mobile", "mobile visitors"]},
        {"id": "Visits_from_Non-Mobile_Devices", "name": "Desktop Visitors", "aliases": ["desktop", "desktop visitors"]},
        {"id": "First_Time_Visits", "name": "New Visitors", "aliases": ["new visitors", "new_visitors", "new"]},
        {"id": "Return_Visits", "name": "Return Visitors", "aliases": ["return visitors", "return_visitors", "returning"]},
    ],
}


@pytest.fixture
def registry() -> MetadataRegistry:
    """Create a registry loaded with sample schema."""
    r = MetadataRegistry()
    r.load_from_dict(SAMPLE_SCHEMA)
    return r


class TestRegistryLoading:
    """Tests for loading behavior."""

    def test_is_loaded(self, registry: MetadataRegistry):
        assert registry.is_loaded is True

    def test_empty_registry(self):
        r = MetadataRegistry()
        assert r.is_loaded is False
        assert r.list_dimensions() == []

    def test_counts(self, registry: MetadataRegistry):
        assert len(registry.list_dimensions()) == 7
        assert len(registry.list_metrics()) == 5
        assert len(registry.list_segments()) == 4

    def test_missing_file_is_ok(self):
        r = MetadataRegistry()
        r.load_from_file("/nonexistent/path/schema.json")
        assert r.is_loaded is False


class TestDimensionResolution:
    """Tests for resolve_dimension()."""

    def test_exact_id(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("variables/page")
        assert result.status == "exact"
        assert result.match == "variables/page"
        assert result.match_name == "Page"
        assert result.confidence == 1.0

    def test_exact_alias(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("page")
        assert result.status == "exact"
        assert result.match == "variables/page"

    def test_alias_case_insensitive(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("PAGE")
        assert result.status == "exact"
        assert result.match == "variables/page"

    def test_alias_underscore(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("referrer_type")
        assert result.status == "exact"
        assert result.match == "variables/referrertype"

    def test_name_match(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("Referrer Type")
        assert result.status == "exact"
        assert result.match == "variables/referrertype"

    def test_fuzzy_match(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("landing page")
        assert result.status == "exact"  # It's an exact alias
        assert result.match == "variables/entrypage"

    def test_not_found(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("zzz_nonexistent_zzz")
        assert result.status == "not_found"

    def test_empty_input(self, registry: MetadataRegistry):
        result = registry.resolve_dimension("")
        assert result.status == "not_found"


class TestMetricResolution:
    """Tests for resolve_metric()."""

    def test_exact_id(self, registry: MetadataRegistry):
        result = registry.resolve_metric("metrics/pageviews")
        assert result.status == "exact"
        assert result.match == "metrics/pageviews"

    def test_alias(self, registry: MetadataRegistry):
        result = registry.resolve_metric("pageviews")
        assert result.status == "exact"
        assert result.match == "metrics/pageviews"

    def test_alternative_alias(self, registry: MetadataRegistry):
        result = registry.resolve_metric("page_views")
        assert result.status == "exact"
        assert result.match == "metrics/pageviews"

    def test_sessions_alias(self, registry: MetadataRegistry):
        result = registry.resolve_metric("sessions")
        assert result.status == "exact"
        assert result.match == "metrics/visits"

    def test_not_found(self, registry: MetadataRegistry):
        result = registry.resolve_metric("revenue_per_click")
        assert result.status in ("not_found", "ambiguous")


class TestSegmentResolution:
    """Tests for resolve_segment()."""

    def test_exact_id(self, registry: MetadataRegistry):
        result = registry.resolve_segment("Visits_from_Mobile_Devices")
        assert result.status == "exact"
        assert result.match == "Visits_from_Mobile_Devices"

    def test_alias(self, registry: MetadataRegistry):
        result = registry.resolve_segment("mobile")
        assert result.status == "exact"
        assert result.match == "Visits_from_Mobile_Devices"

    def test_alias_desktop(self, registry: MetadataRegistry):
        result = registry.resolve_segment("desktop")
        assert result.status == "exact"
        assert result.match == "Visits_from_Non-Mobile_Devices"

    def test_new_visitors(self, registry: MetadataRegistry):
        result = registry.resolve_segment("new visitors")
        assert result.status == "exact"
        assert result.match == "First_Time_Visits"


class TestDisplayNames:
    """Tests for get_*_display() methods."""

    def test_dimension_display(self, registry: MetadataRegistry):
        assert registry.get_dimension_display("variables/page") == "Page"
        assert registry.get_dimension_display("variables/referrertype") == "Referrer Type"

    def test_metric_display(self, registry: MetadataRegistry):
        assert registry.get_metric_display("metrics/pageviews") == "Page Views"
        assert registry.get_metric_display("metrics/visits") == "Visits"

    def test_unknown_display(self, registry: MetadataRegistry):
        assert registry.get_dimension_display("variables/unknown") is None
        assert registry.get_metric_display("metrics/unknown") is None

    def test_segment_display(self, registry: MetadataRegistry):
        assert registry.get_segment_display("Visits_from_Mobile_Devices") == "Mobile Visitors"


class TestListMethods:
    """Tests for list_*() methods."""

    def test_list_dimensions(self, registry: MetadataRegistry):
        dims = registry.list_dimensions()
        assert len(dims) == 7
        assert all("id" in d and "name" in d for d in dims)
        ids = [d["id"] for d in dims]
        assert "variables/page" in ids

    def test_list_metrics(self, registry: MetadataRegistry):
        mets = registry.list_metrics()
        assert len(mets) == 5
        ids = [m["id"] for m in mets]
        assert "metrics/pageviews" in ids

    def test_list_segments(self, registry: MetadataRegistry):
        segs = registry.list_segments()
        assert len(segs) == 4
        ids = [s["id"] for s in segs]
        assert "Visits_from_Mobile_Devices" in ids
