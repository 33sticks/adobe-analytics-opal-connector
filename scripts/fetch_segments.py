"""
One-time utility to discover available Adobe Analytics segment IDs.

Run from project root: python3 -m scripts.fetch_segments
"""

import asyncio


async def main() -> None:
    """Fetch and print available segments from Adobe Analytics."""
    from app.auth.adobe_auth import AdobeAuthManager
    from app.analytics.client import AdobeAnalyticsClient
    from app.config import get_settings

    settings = get_settings()
    auth_manager = AdobeAuthManager(settings)
    client = AdobeAnalyticsClient(auth_manager, settings)

    segments = await client.get_segments(
        rsid=settings.adobe_report_suite_id,
        limit=100,
        include_type="all,shared,templates",
        expansion="definition",
    )
    print(f"Found {len(segments)} segments\n")
    for seg in segments:
        seg_id = seg.get("id", "")
        name = seg.get("name", "")
        description = seg.get("description", "")
        print(f"id: {seg_id}")
        print(f"  name: {name}")
        print(f"  description: {description}")
        if "definition" in seg:
            print(f"  definition: {seg['definition']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
