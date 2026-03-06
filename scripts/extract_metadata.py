"""
Extract Adobe Analytics metadata (dimensions, metrics, segments, calculated metrics).

Generates app/metadata/schema.json for the MetadataRegistry.

Run from project root:
    python3 -m scripts.extract_metadata              # uses default RSID from .env
    python3 -m scripts.extract_metadata --rsid=xxx   # specific report suite
"""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Optional


def _generate_aliases(name: str, adobe_id: str) -> list[str]:
    """Generate search aliases from a name and Adobe ID."""
    aliases = set()
    # Original name as-is
    aliases.add(name)
    # Lowercased
    aliases.add(name.lower())
    # Underscore variant: "Page Views" -> "page_views"
    aliases.add(re.sub(r"\s+", "_", name.lower()))
    # No-space variant: "Page Views" -> "pageviews"
    aliases.add(re.sub(r"\s+", "", name.lower()))
    # Hyphen variant: "Page Views" -> "page-views"
    aliases.add(re.sub(r"\s+", "-", name.lower()))
    # Short ID: "variables/page" -> "page", "metrics/pageviews" -> "pageviews"
    if "/" in adobe_id:
        short = adobe_id.split("/", 1)[1]
        aliases.add(short)
        aliases.add(short.lower())
    return sorted(aliases)


async def main(rsid: Optional[str] = None) -> None:
    """Fetch all metadata from Adobe Analytics and write schema.json."""
    from app.analytics.client import AdobeAnalyticsClient
    from app.auth.adobe_auth import AdobeAuthManager
    from app.config import get_settings

    settings = get_settings()
    auth_manager = AdobeAuthManager(settings)
    client = AdobeAnalyticsClient(auth_manager, settings)
    report_suite = rsid or settings.adobe_report_suite_id

    print(f"Extracting metadata for report suite: {report_suite}")

    # Fetch all in parallel
    dimensions_raw, metrics_raw, segments_raw, calc_metrics_raw = await asyncio.gather(
        client.get_dimensions(report_suite),
        client.get_metrics(report_suite),
        client.get_segments(report_suite, limit=200, include_type="all,shared,templates"),
        client.get_calculated_metrics(report_suite),
    )

    print(f"  Dimensions: {len(dimensions_raw)}")
    print(f"  Metrics: {len(metrics_raw)}")
    print(f"  Segments: {len(segments_raw)}")
    print(f"  Calculated Metrics: {len(calc_metrics_raw)}")

    schema = {
        "rsid": report_suite,
        "dimensions": [],
        "metrics": [],
        "segments": [],
    }

    for dim in dimensions_raw:
        dim_id = dim.get("id", "")
        dim_name = dim.get("name", dim_id)
        if not dim_id:
            continue
        schema["dimensions"].append({
            "id": dim_id,
            "name": dim_name,
            "description": dim.get("description", ""),
            "aliases": _generate_aliases(dim_name, dim_id),
        })

    for met in metrics_raw:
        met_id = met.get("id", "")
        met_name = met.get("name", met_id)
        if not met_id:
            continue
        schema["metrics"].append({
            "id": met_id,
            "name": met_name,
            "description": met.get("description", ""),
            "aliases": _generate_aliases(met_name, met_id),
        })

    # Calculated metrics go into the metrics list too
    for cm in calc_metrics_raw:
        cm_id = cm.get("id", "")
        cm_name = cm.get("name", cm_id)
        if not cm_id:
            continue
        schema["metrics"].append({
            "id": cm_id,
            "name": cm_name,
            "description": cm.get("description", ""),
            "aliases": _generate_aliases(cm_name, cm_id),
        })

    for seg in segments_raw:
        seg_id = seg.get("id", "")
        seg_name = seg.get("name", seg_id)
        if not seg_id:
            continue
        schema["segments"].append({
            "id": seg_id,
            "name": seg_name,
            "description": seg.get("description", ""),
            "aliases": _generate_aliases(seg_name, seg_id),
        })

    # Write schema
    output_path = Path("app/metadata/schema.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"\nSchema written to {output_path}")
    total = len(schema["dimensions"]) + len(schema["metrics"]) + len(schema["segments"])
    print(f"Total entries: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Adobe Analytics metadata")
    parser.add_argument("--rsid", type=str, default=None, help="Report suite ID (default from .env)")
    args = parser.parse_args()
    asyncio.run(main(rsid=args.rsid))
