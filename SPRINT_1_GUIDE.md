# Sprint 1: Foundation — Cursor Implementation Guide

## Overview

Sprint 1 builds the project scaffold, Adobe OAuth, the Analytics API client, and the
discovery endpoint. By the end, you should be able to deploy to Railway and verify that:
1. The health check responds
2. The discovery endpoint returns a valid manifest
3. The app can authenticate with Adobe and pull a basic report

---

## Step 1: Project Scaffold

### Cursor Prompt

```
Read PROJECT_SPEC.md and .cursorrules thoroughly before doing anything.

Create the full project scaffold with:

1. All directories from the spec:
   - app/auth/
   - app/discovery/
   - app/analytics/
   - app/tools/
   - app/utils/
   - tests/

2. Empty __init__.py in every package directory

3. app/config.py with a Pydantic Settings class:
   - adobe_client_id: str
   - adobe_client_secret: str
   - adobe_org_id: str
   - adobe_company_id: str (default "exchane5")
   - adobe_report_suite_id: str (default "33sticksjennwebprops")
   - opal_bearer_token: str
   - port: int = 8000
   - environment: str = "development"
   - log_level: str = "info"
   - Use pydantic-settings BaseSettings with env_file = ".env"
   - Create a cached get_settings() function using lru_cache

4. main.py with:
   - FastAPI app with title "Adobe Analytics Opal Connector"
   - GET / health check endpoint returning {"status": "healthy", "service": "adobe-analytics-opal-connector"}
   - Placeholder comment for route includes (we'll add these next)
   - Startup logging that prints the environment name
   - CORS middleware allowing all origins (for Opal compatibility)

Do NOT create any tool endpoints yet — just the scaffold, config, and health check.
```

### Verify

After Cursor generates this, check:
- `python -c "from app.config import get_settings"` works without errors
- The directory structure matches PROJECT_SPEC.md Section 4

---

## Step 2: Adobe OAuth Token Management

### Cursor Prompt

```
Create app/auth/adobe_auth.py — the Adobe OAuth token manager.

Requirements from the spec:

1. Class: AdobeAuthManager
   - Initialized with settings from app/config.py (use dependency injection)
   - Stores: _access_token (str | None), _token_expiry (float), _lock (asyncio.Lock)

2. Token endpoint:
   POST https://ims-na1.adobelogin.com/ims/token/v3
   Content-Type: application/x-www-form-urlencoded
   Body: grant_type=client_credentials&client_id={id}&client_secret={secret}&scope=openid,AdobeID,additional_info.projectedProductContext

3. Method: async get_token() -> str
   - If current token exists and not expired (with 5-minute buffer), return it
   - Otherwise, acquire the asyncio lock and fetch a new token
   - Double-check after acquiring lock (another coroutine may have refreshed)
   - Parse expires_in from response, calculate expiry timestamp
   - Log token acquisition (but NEVER log the token itself)
   - Raise a clear exception if token fetch fails

4. Method: async _fetch_token() -> tuple[str, int]
   - Use httpx.AsyncClient to POST to the token endpoint
   - Return (access_token, expires_in)
   - Handle HTTP errors with clear error messages
   - Log response status and expires_in (not the token)

5. Create a module-level singleton pattern:
   - _auth_manager: AdobeAuthManager | None = None
   - def get_auth_manager() -> AdobeAuthManager that lazy-initializes using get_settings()

Use httpx (async), not requests. Include type hints and docstrings on all methods.
Do NOT fetch a token at import time — lazy initialization only.
```

### Verify

You can't fully test this without deploying, but check:
- No syntax errors
- The token URL and scope match exactly what worked in your curl test
- The lock pattern prevents race conditions

---

## Step 3: Adobe Analytics API Client

### Cursor Prompt

```
Create app/analytics/client.py — the Adobe Analytics API client.

This client wraps the Adobe Analytics 2.0 Reporting API.

Requirements:

1. Class: AdobeAnalyticsClient
   - Initialized with AdobeAuthManager and Settings
   - Base URL: https://analytics.adobe.io
   - Uses a shared httpx.AsyncClient (created once, reused)

2. Required headers for every request (from .cursorrules):
   Authorization: Bearer {token from auth manager}
   x-api-key: {client_id from settings}
   x-proxy-global-company-id: {company_id from settings}
   Content-Type: application/json

3. Method: async get_report(request_body: dict) -> dict
   - POST to /api/{company_id}/reports
   - Get a fresh token via auth_manager.get_token() for each request
   - Handle 401 by refreshing token and retrying ONCE
   - Handle 429 with exponential backoff (max 3 retries, 1s/2s/4s delays)
   - Handle 403 with a clear permission error message
   - Handle 500+ with a clear Adobe service error message
   - Log request duration for performance monitoring
   - Return the parsed JSON response

4. Method: async get_segments(rsid: str | None = None) -> list[dict]
   - GET to /api/{company_id}/segments
   - Optional query param: rsid={rsid}&limit=50&includeType=shared,all
   - Same auth headers as get_report
   - Returns list of segment objects

5. Module-level singleton:
   - _client: AdobeAnalyticsClient | None = None  
   - def get_analytics_client() -> AdobeAnalyticsClient

6. Important from the real API testing:
   - company_id is "exchane5"
   - report_suite_id is "33sticksjennwebprops"
   - The x-proxy-global-company-id header is REQUIRED or Adobe returns 404
   - Response rows have: data (list of floats), itemId (str), value (str)
   - value may contain HTML entities like &#8220; — note this for later parsing

Use httpx.AsyncClient, not requests. Include proper error handling for all HTTP status codes.
```

### Verify

Check that:
- The headers match exactly what worked in your curl test
- The 401 retry logic refreshes the token before retrying
- The URL construction uses `company_id` from settings, not hardcoded

---

## Step 4: Discovery Endpoint

### Cursor Prompt

```
Create app/discovery/manifest.py and wire it into main.py.

The discovery endpoint is what Opal calls when you register or sync your custom tool.
It returns a JSON manifest describing all available tools.

Requirements:

1. Create app/discovery/manifest.py with:
   - A function get_manifest(base_url: str) -> dict that returns the full tool manifest
   - base_url is the deployed Railway URL (read from an env var or passed in)

2. For Sprint 1, declare TWO tools in the manifest (we'll add more in Sprint 2-3):

   Tool 1: adobe_analytics_traffic
   - Description: "Retrieves page-level traffic data from Adobe Analytics. Use this when users ask about page views, top pages, traffic trends, or website performance over a time period. Available metrics: pageviews, occurrences. Can filter by page name and limit results to top N pages."
   - Parameters:
     - metric (string, optional): "pageviews" or "occurrences", default "pageviews"
     - date_range (string, optional): natural language like "last 7 days", "last week", "this month", default "last 7 days"
     - top_n (integer, optional): number of top pages, default 10, max 50
     - page_filter (string, optional): filter pages containing this string
   - Invocation: POST {base_url}/tools/traffic

   Tool 2: adobe_analytics_referrers
   - Description: "Breaks down website traffic by referrer type from Adobe Analytics. Use this when users ask where their traffic is coming from, about traffic sources, or referral analysis. Shows breakdown by Direct, Organic Search, Paid Search, Social, and Referring Domains."
   - Parameters:
     - metric (string, optional): "pageviews" or "occurrences", default "pageviews"
     - date_range (string, optional): natural language date range, default "last 7 days"
   - Invocation: POST {base_url}/tools/referrers

3. The manifest structure should follow the Opal tool manifest format:
   {
     "schema_version": "v1",
     "tools": [
       {
         "name": "...",
         "description": "...",
         "parameters": [...],
         "invocation": { "url": "...", "method": "POST", "headers": {"Content-Type": "application/json"} }
       }
     ]
   }

4. Wire into main.py:
   - GET /discovery endpoint that returns get_manifest(base_url)
   - base_url should come from an env var BASE_URL (for Railway deployment)
   - Default to "http://localhost:8000" in development

5. Add base_url to the Settings class in config.py:
   - base_url: str = "http://localhost:8000"

The tool descriptions are CRITICAL — Opal uses them to decide when to invoke the tool.
Make them specific about what data is available and when to use the tool.
```

### Verify

- Run the app locally: `uvicorn main:app --reload`
- Hit `http://localhost:8000/` → should return health check JSON
- Hit `http://localhost:8000/discovery` → should return the manifest with 2 tools
- Verify the manifest JSON is valid and tool descriptions are clear

---

## Step 5: Stub Tool Endpoints

### Cursor Prompt

```
Create stub endpoints for the two Sprint 1 tools so the app is deployable and
Opal can successfully invoke them (even though they won't query Adobe yet).

1. Create app/tools/traffic_analysis.py:
   - FastAPI APIRouter with prefix="/tools"
   - POST /tools/traffic endpoint
   - Accept the request body as a dict (Opal sends flexible JSON)
   - Extract parameters — handle both nested (body["parameters"]["metric"]) 
     and flat (body["metric"]) formats as noted in .cursorrules
   - For now, return a stub response:
     {
       "status": "success",
       "message": "Traffic analysis tool received your request. Parameters: metric={metric}, date_range={date_range}, top_n={top_n}, page_filter={page_filter}. Full implementation coming in Sprint 2.",
       "data": {}
     }

2. Create app/tools/referrer_breakdown.py:
   - Same pattern as above
   - POST /tools/referrers endpoint
   - Stub response echoing back the received parameters

3. Create a helper function in app/tools/__init__.py or a shared utility:
   - extract_parameters(body: dict) -> dict
   - Handles the Opal request format: checks for body["parameters"] first,
     falls back to flat body keys
   - Coerces top_n to int if it arrives as a string
   - Applies defaults: metric="pageviews", date_range="last 7 days", top_n=10

4. Wire both routers into main.py using app.include_router()

5. Add Opal bearer token validation as a FastAPI dependency:
   - Create app/auth/opal_auth.py
   - A dependency function verify_opal_token(authorization: str = Header(...))
   - Extracts the Bearer token from the Authorization header
   - Compares against settings.opal_bearer_token
   - Returns 401 if missing or mismatched
   - Apply this dependency to the tool endpoints (but NOT to / or /discovery)
```

### Verify

- `POST http://localhost:8000/tools/traffic` with a JSON body returns the stub response
- The parameter extraction handles both nested and flat formats
- Missing the Authorization header returns 401

---

## Step 6: Local Integration Test

### Cursor Prompt

```
Create a simple test script at tests/test_integration.py that verifies the full
local stack works before deploying to Railway.

The script should:

1. Test health check: GET / returns 200 with status "healthy"

2. Test discovery: GET /discovery returns 200 with valid manifest containing 2 tools

3. Test traffic stub (nested params format):
   POST /tools/traffic with:
   Headers: Authorization: Bearer {test_token}
   Body: {"tool_name": "adobe_analytics_traffic", "parameters": {"metric": "pageviews", "date_range": "last 7 days", "top_n": "10"}}
   → Should return 200 with status "success"

4. Test traffic stub (flat params format):
   POST /tools/traffic with:
   Headers: Authorization: Bearer {test_token}
   Body: {"metric": "pageviews", "date_range": "last 7 days", "top_n": 10}
   → Should also return 200 with status "success"

5. Test auth rejection:
   POST /tools/traffic WITHOUT Authorization header → Should return 401

Use pytest with httpx.AsyncClient and FastAPI's TestClient.
Set OPAL_BEARER_TOKEN=test_token_123 in test fixtures.

Also create a quick manual test script at scripts/test_adobe_auth.py that:
- Loads settings from .env
- Instantiates AdobeAuthManager
- Calls get_token()
- Prints "Token acquired, expires in X seconds" (NOT the token itself)
- Then uses AdobeAnalyticsClient to fetch a basic 5-row report
- Prints the response summary: number of rows, total page views

This manual script is for verifying the Adobe connection works before deploying.
Run it with: python -m scripts.test_adobe_auth
```

### Verify

- `pytest tests/test_integration.py` passes all 5 tests
- `python -m scripts.test_adobe_auth` (with your .env populated) prints real data from Adobe

---

## Step 7: Deploy to Railway

### Manual Steps (not Cursor)

1. **Create a GitHub repo** for the project and push your code

2. **Create a new Railway project:**
   - Connect your GitHub repo
   - Railway will detect the Procfile automatically

3. **Set environment variables in Railway dashboard:**
   ```
   ADOBE_CLIENT_ID=a86d9fb26d054419b84abc384bb8f1fd
   ADOBE_CLIENT_SECRET=(your secret)
   ADOBE_ORG_ID=DCF77919596885950A495D3E@AdobeOrg
   ADOBE_COMPANY_ID=exchane5
   ADOBE_REPORT_SUITE_ID=33sticksjennwebprops
   OPAL_BEARER_TOKEN=(generate a strong random string)
   BASE_URL=(your Railway URL, e.g., https://your-app.up.railway.app)
   ENVIRONMENT=production
   LOG_LEVEL=info
   ```

4. **Deploy and verify:**
   - Hit `https://your-app.up.railway.app/` → health check
   - Hit `https://your-app.up.railway.app/discovery` → manifest JSON

5. **Register in Opal (optional — can wait for Sprint 2):**
   - Opal admin → Tools → Add Custom Tool
   - Discovery URL: `https://your-app.up.railway.app/discovery`
   - Click Sync → verify tools appear

---

## Sprint 1 Checklist

After completing all steps, verify:

- [ ] Project structure matches the spec
- [ ] `uvicorn main:app --reload` starts without errors
- [ ] GET `/` returns health check JSON
- [ ] GET `/discovery` returns manifest with 2 tools
- [ ] POST `/tools/traffic` with valid auth returns stub response
- [ ] POST `/tools/traffic` without auth returns 401
- [ ] Parameter extraction handles nested and flat formats
- [ ] `scripts/test_adobe_auth.py` successfully authenticates and pulls a report
- [ ] All pytest tests pass
- [ ] Deployed to Railway and health check works remotely
- [ ] Discovery endpoint accessible at Railway URL

---

## Notes for Sprint 2

Once Sprint 1 is solid, Sprint 2 will:
1. Build the date_parser to convert natural language dates to Adobe ISO format
2. Build the query_builder to construct Adobe API request bodies
3. Build the response_parser to transform Adobe responses into clean data
4. Replace the traffic stub with a real end-to-end implementation
5. Replace the referrer stub with a real end-to-end implementation
6. Register both tools in Opal and test via Chat

I'll generate the Sprint 2 guide when you're ready.
