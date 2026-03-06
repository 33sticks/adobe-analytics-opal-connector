"""Adobe Analytics 2.0 API client for reports and segments."""

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from app.auth.adobe_auth import AdobeAuthManager
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

BASE_URL = "https://analytics.adobe.io"
RATE_LIMIT_BACKOFF = [1, 2, 4]  # seconds for 429 retries


class AdobeAnalyticsError(Exception):
    """Raised when Adobe Analytics API requests fail."""

    pass


class AdobeAnalyticsClient:
    """Wraps the Adobe Analytics 2.0 Reporting and Segments APIs."""

    def __init__(self, auth_manager: AdobeAuthManager, settings: Settings) -> None:
        """Initialize with auth manager and settings."""
        self.auth_manager = auth_manager
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=60.0,
        )

    async def _build_headers(self) -> dict[str, str]:
        """Build request headers with fresh token."""
        token = await self.auth_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": self.settings.adobe_client_id,
            "x-proxy-global-company-id": self.settings.adobe_company_id,
            "Content-Type": "application/json",
        }

    async def get_report(self, request_body: dict[str, Any]) -> dict[str, Any]:
        """
        POST a report request to Adobe Analytics and return the parsed JSON.

        Response rows have: data (list of floats), itemId (str), value (str).
        value may contain HTML entities like &#8220; — decode in response_parser.

        Handles 401 (retry once after token refresh), 429 (exponential backoff),
        403, and 500+ with clear error messages.
        """
        company_id = self.settings.adobe_company_id
        url = f"/api/{company_id}/reports"
        headers = await self._build_headers()

        start = time.perf_counter()
        response = await self._client.post(url, json=request_body, headers=headers)
        duration_ms = (time.perf_counter() - start) * 1000

        if response.status_code == 200:
            logger.info(
                "Adobe report fetched",
                extra={"duration_ms": round(duration_ms, 2), "url": url},
            )
            return response.json()

        if response.status_code == 401:
            logger.warning("Adobe token rejected (401), refreshing and retrying once")
            self.auth_manager.invalidate_token()
            headers = await self._build_headers()
            response = await self._client.post(url, json=request_body, headers=headers)
            if response.status_code == 200:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "Adobe report fetched after token refresh",
                    extra={"duration_ms": round(duration_ms, 2), "url": url},
                )
                return response.json()
            raise AdobeAnalyticsError(
                f"Adobe Analytics authentication failed after token refresh: HTTP {response.status_code}"
            )

        if response.status_code == 403:
            raise AdobeAnalyticsError(
                "Adobe Analytics permission denied. Check API access and report suite permissions."
            )

        if response.status_code == 429:
            for attempt, delay in enumerate(RATE_LIMIT_BACKOFF):
                logger.warning(
                    "Adobe rate limited (429), backing off",
                    extra={"attempt": attempt + 1, "delay_s": delay},
                )
                await asyncio.sleep(delay)
                headers = await self._build_headers()
                response = await self._client.post(url, json=request_body, headers=headers)
                if response.status_code == 200:
                    duration_ms = (time.perf_counter() - start) * 1000
                    logger.info(
                        "Adobe report fetched after rate limit retry",
                        extra={"duration_ms": round(duration_ms, 2), "url": url},
                    )
                    return response.json()
            raise AdobeAnalyticsError(
                "Adobe Analytics rate limit exceeded. Please try again later."
            )

        if response.status_code >= 500:
            raise AdobeAnalyticsError(
                f"Adobe Analytics service error (HTTP {response.status_code}). Please try again later."
            )

        raise AdobeAnalyticsError(
            f"Adobe Analytics request failed: HTTP {response.status_code}"
        )

    async def get_segments(
        self,
        rsid: Optional[str] = None,
        *,
        limit: int = 50,
        include_type: str = "shared,all",
        expansion: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        GET available segments from Adobe Analytics.

        Optional rsid filters by report suite. Defaults to settings.adobe_report_suite_id.
        Returns list of segment objects (id, name, description, rsid, owner, etc.).
        """
        company_id = self.settings.adobe_company_id
        report_suite = rsid or self.settings.adobe_report_suite_id
        params: dict[str, Any] = {
            "rsid": report_suite,
            "limit": limit,
            "includeType": include_type,
        }
        if expansion:
            params["expansion"] = expansion
        url = f"/api/{company_id}/segments"
        headers = await self._build_headers()

        start = time.perf_counter()
        response = await self._client.get(url, params=params, headers=headers)
        duration_ms = (time.perf_counter() - start) * 1000

        if response.status_code == 200:
            logger.info(
                "Adobe segments fetched",
                extra={"duration_ms": round(duration_ms, 2), "rsid": report_suite},
            )
            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "content" in data:
                return data["content"]
            return []

        if response.status_code == 401:
            logger.warning("Adobe token rejected (401), refreshing and retrying once")
            self.auth_manager.invalidate_token()
            headers = await self._build_headers()
            response = await self._client.get(url, params=params, headers=headers)
            if response.status_code == 200:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "Adobe segments fetched after token refresh",
                    extra={"duration_ms": round(duration_ms, 2), "rsid": report_suite},
                )
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "content" in data:
                    return data["content"]
                return []
            raise AdobeAnalyticsError(
                f"Adobe Analytics authentication failed after token refresh: HTTP {response.status_code}"
            )

        if response.status_code == 403:
            raise AdobeAnalyticsError(
                "Adobe Analytics permission denied. Check API access and report suite permissions."
            )

        if response.status_code == 429:
            for attempt, delay in enumerate(RATE_LIMIT_BACKOFF):
                logger.warning(
                    "Adobe rate limited (429), backing off",
                    extra={"attempt": attempt + 1, "delay_s": delay},
                )
                await asyncio.sleep(delay)
                headers = await self._build_headers()
                response = await self._client.get(url, params=params, headers=headers)
                if response.status_code == 200:
                    duration_ms = (time.perf_counter() - start) * 1000
                    logger.info(
                        "Adobe segments fetched after rate limit retry",
                        extra={"duration_ms": round(duration_ms, 2), "rsid": report_suite},
                    )
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "content" in data:
                        return data["content"]
                    return []
            raise AdobeAnalyticsError(
                "Adobe Analytics rate limit exceeded. Please try again later."
            )

        if response.status_code >= 500:
            raise AdobeAnalyticsError(
                f"Adobe Analytics service error (HTTP {response.status_code}). Please try again later."
            )

        raise AdobeAnalyticsError(
            f"Adobe Analytics request failed: HTTP {response.status_code}"
        )


    async def _get_paginated(
        self,
        url: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """GET a paginated Adobe API endpoint, handling auth retry, rate limits, and pagination."""
        all_items: list[dict[str, Any]] = []
        page = 0

        while True:
            params["page"] = page
            headers = await self._build_headers()
            start = time.perf_counter()
            response = await self._client.get(url, params=params, headers=headers)
            duration_ms = (time.perf_counter() - start) * 1000

            if response.status_code == 401:
                logger.warning("Adobe token rejected (401), refreshing and retrying once")
                self.auth_manager.invalidate_token()
                headers = await self._build_headers()
                response = await self._client.get(url, params=params, headers=headers)
                if response.status_code != 200:
                    raise AdobeAnalyticsError(
                        f"Adobe Analytics authentication failed after token refresh: HTTP {response.status_code}"
                    )

            if response.status_code == 429:
                for attempt, delay in enumerate(RATE_LIMIT_BACKOFF):
                    logger.warning(
                        "Adobe rate limited (429), backing off",
                        extra={"attempt": attempt + 1, "delay_s": delay},
                    )
                    await asyncio.sleep(delay)
                    headers = await self._build_headers()
                    response = await self._client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        break
                else:
                    raise AdobeAnalyticsError(
                        "Adobe Analytics rate limit exceeded. Please try again later."
                    )

            if response.status_code == 403:
                raise AdobeAnalyticsError(
                    "Adobe Analytics permission denied. Check API access and report suite permissions."
                )

            if response.status_code >= 500:
                raise AdobeAnalyticsError(
                    f"Adobe Analytics service error (HTTP {response.status_code}). Please try again later."
                )

            if response.status_code != 200:
                raise AdobeAnalyticsError(
                    f"Adobe Analytics request failed: HTTP {response.status_code}"
                )

            data = response.json()
            logger.info(
                "Adobe API page fetched",
                extra={"duration_ms": round(duration_ms, 2), "url": url, "page": page},
            )

            if isinstance(data, list):
                all_items.extend(data)
                break
            if isinstance(data, dict) and "content" in data:
                items = data["content"]
                if isinstance(items, list):
                    all_items.extend(items)
                if data.get("lastPage", True):
                    break
                page += 1
            else:
                break

        return all_items

    async def get_dimensions(
        self,
        rsid: Optional[str] = None,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """GET available dimensions from Adobe Analytics for a report suite."""
        company_id = self.settings.adobe_company_id
        report_suite = rsid or self.settings.adobe_report_suite_id
        url = f"/api/{company_id}/dimensions"
        params: dict[str, Any] = {"rsid": report_suite, "limit": limit}
        return await self._get_paginated(url, params)

    async def get_metrics(
        self,
        rsid: Optional[str] = None,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """GET available metrics from Adobe Analytics for a report suite."""
        company_id = self.settings.adobe_company_id
        report_suite = rsid or self.settings.adobe_report_suite_id
        url = f"/api/{company_id}/metrics"
        params: dict[str, Any] = {"rsid": report_suite, "limit": limit}
        return await self._get_paginated(url, params)

    async def get_calculated_metrics(
        self,
        rsid: Optional[str] = None,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """GET available calculated metrics from Adobe Analytics."""
        company_id = self.settings.adobe_company_id
        report_suite = rsid or self.settings.adobe_report_suite_id
        url = f"/api/{company_id}/calculatedmetrics"
        params: dict[str, Any] = {"rsid": report_suite, "limit": limit}
        return await self._get_paginated(url, params)


_client: Optional[AdobeAnalyticsClient] = None


def get_analytics_client() -> AdobeAnalyticsClient:
    """Return the singleton AdobeAnalyticsClient, lazy-initialized."""
    global _client
    if _client is None:
        from app.auth.adobe_auth import get_auth_manager

        _client = AdobeAnalyticsClient(get_auth_manager(), get_settings())
    return _client
