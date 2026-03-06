"""MetadataRegistry — resolves dimension, metric, and segment names via fuzzy matching."""

import json
import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ResolveResult:
    """Result of resolving a name to an Adobe Analytics ID."""

    status: str  # "exact", "fuzzy", "ambiguous", "not_found"
    match: Optional[str] = None  # Adobe ID (e.g. "variables/page")
    match_name: Optional[str] = None  # Display name (e.g. "Page")
    confidence: float = 0.0
    suggestions: list[dict] = field(default_factory=list)  # [{"id": ..., "name": ..., "score": ...}]
    message: Optional[str] = None


@dataclass
class SchemaEntry:
    """A single dimension, metric, or segment from the schema."""

    id: str
    name: str
    aliases: list[str] = field(default_factory=list)


class MetadataRegistry:
    """Loaded once on startup from schema.json. Provides fuzzy resolution for dimensions, metrics, segments."""

    def __init__(self) -> None:
        self.dimensions: list[SchemaEntry] = []
        self.metrics: list[SchemaEntry] = []
        self.segments: list[SchemaEntry] = []
        self._loaded = False

    def load_from_file(self, path: str) -> None:
        """Load schema from a JSON file. Silently skip if file doesn't exist."""
        schema_path = Path(path)
        if not schema_path.exists():
            logger.warning("Schema file not found: %s — registry will be empty", path)
            return
        with open(schema_path) as f:
            data = json.load(f)
        self._load_data(data)

    def load_from_dict(self, data: dict) -> None:
        """Load schema from a dict (for testing)."""
        self._load_data(data)

    def _load_data(self, data: dict) -> None:
        self.dimensions = [
            SchemaEntry(id=d["id"], name=d["name"], aliases=d.get("aliases", []))
            for d in data.get("dimensions", [])
        ]
        self.metrics = [
            SchemaEntry(id=d["id"], name=d["name"], aliases=d.get("aliases", []))
            for d in data.get("metrics", [])
        ]
        self.segments = [
            SchemaEntry(id=d["id"], name=d["name"], aliases=d.get("aliases", []))
            for d in data.get("segments", [])
        ]
        self._loaded = True
        logger.info(
            "Metadata registry loaded: %d dimensions, %d metrics, %d segments",
            len(self.dimensions),
            len(self.metrics),
            len(self.segments),
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def resolve_dimension(self, name: str) -> ResolveResult:
        """Resolve a dimension name to its Adobe ID."""
        return self._resolve(name, self.dimensions, "dimension")

    def resolve_metric(self, name: str) -> ResolveResult:
        """Resolve a metric name to its Adobe ID."""
        return self._resolve(name, self.metrics, "metric")

    def resolve_segment(self, name: str) -> ResolveResult:
        """Resolve a segment name to its Adobe ID."""
        return self._resolve(name, self.segments, "segment")

    def get_dimension_display(self, adobe_id: str) -> Optional[str]:
        """Get display name for a dimension ID."""
        for entry in self.dimensions:
            if entry.id == adobe_id:
                return entry.name
        return None

    def get_metric_display(self, adobe_id: str) -> Optional[str]:
        """Get display name for a metric ID."""
        for entry in self.metrics:
            if entry.id == adobe_id:
                return entry.name
        return None

    def get_segment_display(self, adobe_id: str) -> Optional[str]:
        """Get display name for a segment ID."""
        for entry in self.segments:
            if entry.id == adobe_id:
                return entry.name
        return None

    def list_dimensions(self) -> list[dict]:
        """Return all dimensions as [{"id": ..., "name": ...}]."""
        return [{"id": e.id, "name": e.name} for e in self.dimensions]

    def list_metrics(self) -> list[dict]:
        """Return all metrics as [{"id": ..., "name": ...}]."""
        return [{"id": e.id, "name": e.name} for e in self.metrics]

    def list_segments(self) -> list[dict]:
        """Return all segments as [{"id": ..., "name": ...}]."""
        return [{"id": e.id, "name": e.name} for e in self.segments]

    def _resolve(self, name: str, entries: list[SchemaEntry], kind: str) -> ResolveResult:
        """Tiered resolution: exact ID → exact alias → normalized → fuzzy."""
        if not name or not name.strip():
            return ResolveResult(
                status="not_found",
                message=f"Empty {kind} name provided.",
            )

        query = name.strip()
        normalized = _normalize(query)

        # Tier 1: Exact ID match
        for entry in entries:
            if entry.id == query:
                return ResolveResult(
                    status="exact",
                    match=entry.id,
                    match_name=entry.name,
                    confidence=1.0,
                )

        # Tier 2: Exact alias match (case-insensitive)
        # Collect all matches — prefer canonical ID (where query matches the short ID form)
        alias_matches = []
        for entry in entries:
            if normalized in [_normalize(a) for a in entry.aliases] or normalized == _normalize(entry.name):
                alias_matches.append(entry)

        if alias_matches:
            if len(alias_matches) == 1:
                return ResolveResult(
                    status="exact",
                    match=alias_matches[0].id,
                    match_name=alias_matches[0].name,
                    confidence=1.0,
                )
            # Multiple alias matches — prefer entry whose short ID matches the query
            # e.g. "metrics/pageviews" wins over "metrics/event4" for "pageviews" or "page_views"
            query_collapsed = re.sub(r"[_\-\s]+", "", normalized)
            for entry in alias_matches:
                short_id = entry.id.rsplit("/", 1)[-1] if "/" in entry.id else entry.id
                short_collapsed = re.sub(r"[_\-\s]+", "", short_id.lower())
                if short_collapsed == query_collapsed:
                    return ResolveResult(
                        status="exact",
                        match=entry.id,
                        match_name=entry.name,
                        confidence=1.0,
                    )
            # No canonical match — return first
            return ResolveResult(
                status="exact",
                match=alias_matches[0].id,
                match_name=alias_matches[0].name,
                confidence=1.0,
            )

        # Tier 3: Normalized substring match (query contained in name/alias or vice versa)
        substring_matches = []
        for entry in entries:
            entry_normalized = _normalize(entry.name)
            if normalized in entry_normalized or entry_normalized in normalized:
                substring_matches.append(entry)
            else:
                for alias in entry.aliases:
                    if normalized in _normalize(alias) or _normalize(alias) in normalized:
                        substring_matches.append(entry)
                        break

        if len(substring_matches) == 1:
            return ResolveResult(
                status="fuzzy",
                match=substring_matches[0].id,
                match_name=substring_matches[0].name,
                confidence=0.85,
                message=f"Matched '{query}' to '{substring_matches[0].name}'.",
            )

        # Tier 4: SequenceMatcher fuzzy matching
        scored: list[tuple[float, SchemaEntry]] = []
        for entry in entries:
            best_score = SequenceMatcher(None, normalized, _normalize(entry.name)).ratio()
            for alias in entry.aliases:
                score = SequenceMatcher(None, normalized, _normalize(alias)).ratio()
                best_score = max(best_score, score)
            if best_score >= 0.5:
                scored.append((best_score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return ResolveResult(
                status="not_found",
                message=f"No matching {kind} found for '{query}'.",
            )

        top_score, top_entry = scored[0]

        # High confidence: single clear winner
        if top_score >= 0.7:
            # Check if there's a close second
            if len(scored) > 1 and scored[1][0] >= top_score - 0.05:
                return ResolveResult(
                    status="ambiguous",
                    confidence=top_score,
                    suggestions=[
                        {"id": e.id, "name": e.name, "score": round(s, 3)}
                        for s, e in scored[:5]
                    ],
                    message=f"Multiple {kind}s match '{query}'. Please clarify.",
                )
            return ResolveResult(
                status="fuzzy",
                match=top_entry.id,
                match_name=top_entry.name,
                confidence=top_score,
                message=f"Matched '{query}' to '{top_entry.name}' (confidence: {top_score:.0%}).",
            )

        # Low confidence: return suggestions
        return ResolveResult(
            status="ambiguous" if len(scored) > 1 else "not_found",
            confidence=top_score,
            suggestions=[
                {"id": e.id, "name": e.name, "score": round(s, 3)}
                for s, e in scored[:5]
            ],
            message=f"No confident match for '{query}'. Did you mean one of these?",
        )


def _normalize(s: str) -> str:
    """Normalize a name for comparison: lowercase, strip, collapse separators."""
    s = s.strip().lower()
    s = re.sub(r"[_\-./\s]+", " ", s)
    return s


# Singleton registry
_registry: Optional[MetadataRegistry] = None


def get_registry() -> MetadataRegistry:
    """Return the singleton MetadataRegistry, lazy-initialized from config."""
    global _registry
    if _registry is None:
        _registry = MetadataRegistry()
        try:
            from app.config import get_settings
            settings = get_settings()
            _registry.load_from_file(settings.metadata_schema_path)
        except Exception:
            logger.warning("Could not load metadata schema on startup — registry will be empty")
    return _registry
