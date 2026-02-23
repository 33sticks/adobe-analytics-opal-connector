# Adobe Analytics Connector for Optimizely Opal

## Project Spec & Implementation Guide

**Project:** Adobe Analytics Opal Tool
**Author:** 33 Sticks
**Version:** 1.0
**Deployment:** Railway
**Stack:** Python / FastAPI

---

## 1. Project Overview

### What We're Building

A custom Optimizely Opal tool that enables natural language conversations about Adobe Analytics data directly within Opal Chat. Users ask questions like "What were the top 10 pages by page views last week?" and receive formatted, actionable answers without leaving Optimizely.

### Architecture Pattern

This follows the same proven pattern as the Test Readiness Analyzer:

```
User (Opal Chat) → Opal Agent → Tool Registry → Our FastAPI Service → Adobe Analytics 2.0 API → Formatted Response → Opal Chat
```

### Key Difference from Test Readiness Analyzer

The Test Readiness Analyzer does self-contained computation — it receives parameters and returns analysis. This tool makes **real-time external API calls** to Adobe Analytics, which adds:

- Authentication management (OAuth token lifecycle)
- External API latency
- Data transformation from Adobe's response format to Opal-friendly output
- Error handling for API failures, rate limits, and permission issues

---

## 2. Available Data in Sandbox

**Important:** The Adobe Analytics sandbox contains basic web analytics data only. All tool capabilities must be designed around this data.

**Company ID:** exchane5
**Report Suite ID:** 33sticksjennwebprops

### Data Characteristics

- ~80 unique pages total
- Low traffic site (~4,800 page views in a 3-week February window)
- Page names use " > " as a section delimiter (e.g., "DDT Blog > post > title here")
- Some page names contain HTML entities (e.g., `&#8220;`) — must decode in response parser

### Sample API Response (actual)

```json
{
  "totalPages": 16,
  "firstPage": true,
  "lastPage": false,
  "numberOfElements": 5,
  "number": 0,
  "totalElements": 80,
  "rows": [
    {"data": [3352.0], "itemId": "2439908651", "value": "beacon parser > beacon parsed successfully"},
    {"data": [983.0], "itemId": "2437100290", "value": "beacon parser > main"},
    {"data": [119.0], "itemId": "3568101380", "value": "DDT Blog > post > how i got onetrust to work with adobe launch"},
    {"data": [101.0], "itemId": "3324792768", "value": "DDT Blog > homepage >"},
    {"data": [35.0], "itemId": "3865949280", "value": "DDT Blog > post > problems with the &#8220;autoblock&#8221; approach to consent management"}
  ],
  "summaryData": {
    "filteredTotals": [4832.0],
    "totals": [4832.0]
  }
}
```

### Dimensions Available

- `variables/page` — Page Name (e.g., "/home", "/about", "/contact", "/pricing")
- `variables/referrertype` — Referrer Type (e.g., "Direct", "Organic Search", "Paid Search", "Social", "Referring Domains")
- `variables/daterangeday` — Date (day-level granularity)

### Metrics Available

- `metrics/pageviews` — Page Views
- `metrics/occurrences` — Occurrences (server calls / hits)

### Segments Available

- Basic out-of-the-box segments (e.g., Mobile Visitors, Tablet Visitors, Desktop Visitors, Return Visitors, New Visitors)
- No custom segments

### What We Do NOT Have

- Revenue / conversion data
- Custom eVars or props
- Product data
- Campaign tracking dimensions
- Custom calculated metrics
- Pathing data

---

## 3. Use Cases (Priority Order)

### UC1: Traffic Analysis — "Top Pages"

**Example Queries:**

- "What were the top 10 pages by page views last week?"
- "How did traffic to the homepage compare this month vs last month?"
- "Show me daily page views for the last 30 days."

**Adobe API Translation:**

- Dimension: `variables/page`
- Metric: `metrics/pageviews`
- Date range: parsed from natural language
- Sort: descending by metric
- Limit: top N

**Response Format:**

```
Here are the top 10 pages by page views for last week (Feb 10–16, 2026):

1. /home — 12,450 page views
2. /products — 8,230 page views
3. /about — 4,120 page views
...

Total page views across all pages: 45,670
```

---

### UC2: Referrer Breakdown

**Example Queries:**

- "Where is my traffic coming from? Break it down by referrer type for the last 30 days."
- "What percentage of traffic to product pages is organic search vs direct?"

**Adobe API Translation:**

- Dimension: `variables/referrertype`
- Metric: `metrics/pageviews` or `metrics/occurrences`
- Date range: parsed from natural language
- Optional filter: page name filter for specific pages

**Response Format:**

```
Traffic breakdown by referrer type (last 30 days):

- Direct: 15,200 (42%)
- Organic Search: 10,800 (30%)
- Referring Domains: 6,500 (18%)
- Social: 2,300 (6%)
- Paid Search: 1,400 (4%)

Total: 36,200 page views
```

---

### UC3: Page Performance Comparison

**Example Queries:**

- "Compare page views for /home, /about, and /contact over the last 14 days."
- "Which pages had the biggest increase in traffic week over week?"

**Adobe API Translation:**

- Multiple API calls or itemId filtering for specific pages
- Two date ranges for comparison queries
- Tool-side computation: percent change, ranking

**Response Format:**

```
Page comparison (last 14 days vs prior 14 days):

Page         | This Period | Prior Period | Change
/home        | 24,900      | 22,100       | +12.7%
/about       | 8,240       | 8,890        | -7.3%
/contact     | 3,100       | 2,950        | +5.1%
```

---

### UC4: Segment-Level Insights

**Example Queries:**

- "How do page views differ between mobile and desktop visitors this month?"
- "Show me traffic from returning visitors to the top 5 pages."

**Adobe API Translation:**

- Apply segment ID to the report request
- Requires mapping segment names to segment IDs (fetched via Segments API or hardcoded for sandbox)

**Response Format:**

```
Page views by device type (this month):

Page         | Mobile  | Desktop | Difference
/home        | 5,200   | 7,250   | Desktop +39%
/products    | 3,800   | 4,430   | Desktop +17%
/about       | 2,100   | 2,020   | Mobile +4%
```

---

### UC5: Pre-Experiment Traffic Validation

**Example Queries:**

- "Does the /pricing page get enough traffic for a 2-week A/B test? Show me daily page views for the last 30 days."
- "What's the average daily traffic to the homepage?"

**Adobe API Translation:**

- Dimension: `variables/daterangeday`
- Metric: `metrics/pageviews`
- Filter: specific page
- Date range: last 30 days

**Tool-Side Computation:**

- Daily average
- Min/max daily traffic
- Trend direction
- Simple assessment: "At X page views/day, a 2-week test would accumulate ~Y total visitors."

**Response Format:**

```
Traffic analysis for /pricing (last 30 days):

- Daily average: 342 page views
- Range: 187 (low, Sundays) to 498 (high, Tuesdays)
- Trend: Stable (no significant increase or decrease)

For a 2-week test: ~4,788 estimated total page views
Note: This is page views, not unique visitors. Actual sample size
for statistical significance depends on your conversion rate and
minimum detectable effect.
```

---

## 4. Technical Architecture

### Directory Structure

```
adobe-analytics-opal-connector/
├── main.py                     # FastAPI app entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Railway deployment config
├── .env.example                # Template for environment variables
├── .cursorrules                # Cursor AI context
├── PROJECT_SPEC.md             # This file
│
├── app/
│   ├── __init__.py
│   ├── config.py               # Environment config & settings
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   └── adobe_auth.py       # OAuth token management
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   └── manifest.py         # Opal tool discovery endpoint
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── client.py           # Adobe Analytics API client
│   │   ├── query_builder.py    # Builds AA report requests
│   │   └── response_parser.py  # Parses AA responses into clean data
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── traffic_analysis.py     # UC1: Top pages, page view trends
│   │   ├── referrer_breakdown.py   # UC2: Traffic source analysis
│   │   ├── page_comparison.py      # UC3: Compare pages, period-over-period
│   │   ├── segment_insights.py     # UC4: Segment-level breakdowns
│   │   └── traffic_validation.py   # UC5: Pre-experiment traffic check
│   │
│   └── utils/
│       ├── __init__.py
│       ├── date_parser.py      # Natural language date range parsing
│       └── formatters.py       # Response formatting helpers
│
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_query_builder.py
    ├── test_response_parser.py
    ├── test_date_parser.py
    └── test_tools.py
```

---

### Component Details

#### A. `main.py` — FastAPI App Entry Point

```python
# Endpoints to implement:
# GET  /                    → Health check
# GET  /discovery           → Opal tool manifest (JSON)
# POST /tools/traffic       → UC1: Traffic analysis
# POST /tools/referrers     → UC2: Referrer breakdown
# POST /tools/compare       → UC3: Page comparison
# POST /tools/segments      → UC4: Segment insights
# POST /tools/validation    → UC5: Traffic validation
```

Each tool endpoint receives parameters from Opal and returns a JSON response.

---

#### B. `app/auth/adobe_auth.py` — OAuth Token Management

**Authentication Flow: OAuth Server-to-Server (v2)**

Adobe deprecated JWT auth. Use the newer OAuth Server-to-Server credentials.

**Token Request:**

```
POST https://ims-na1.adobelogin.com/ims/token/v3
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={CLIENT_ID}
&client_secret={CLIENT_SECRET}
&scope=openid,AdobeID,read_organizations,additional_info.projectedProductContext
```

**Token Response:**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86399
}
```

**Implementation Requirements:**

- Cache the access token in memory
- Track expiration time (subtract 5-minute buffer)
- Auto-refresh when expired
- Thread-safe token access (use asyncio lock)
- Expose `get_token()` async method that always returns a valid token

**Environment Variables Required:**

```
ADOBE_CLIENT_ID=xxx
ADOBE_CLIENT_SECRET=xxx
ADOBE_ORG_ID=xxx
ADOBE_COMPANY_ID=xxx          # Also called "global company ID" in Adobe
ADOBE_REPORT_SUITE_ID=xxx     # The report suite to query
```

---

#### C. `app/discovery/manifest.py` — Opal Discovery Endpoint

The discovery endpoint tells Opal what this tool can do. Opal calls `GET /discovery` when you register or sync the tool.

**Manifest Structure:**

Each tool (UC1–UC5) is declared as a separate tool in the manifest, OR you can declare a single tool with a flexible parameter schema. Recommended approach: **one tool per use case** for clarity.

**Example Tool Declaration (UC1: Traffic Analysis):**

```json
{
  "schema_version": "v1",
  "name": "adobe_analytics_traffic",
  "description": "Retrieves page-level traffic data from Adobe Analytics. Use this tool when users ask about page views, top pages, traffic trends, or page-level performance over a time period.",
  "parameters": [
    {
      "name": "metric",
      "type": "string",
      "description": "The metric to retrieve. Options: 'pageviews' or 'occurrences'. Default: 'pageviews'.",
      "required": false
    },
    {
      "name": "date_range",
      "type": "string",
      "description": "The time period to analyze, in natural language. Examples: 'last 7 days', 'last week', 'this month', 'last 30 days', 'February 2026'. Default: 'last 7 days'.",
      "required": false
    },
    {
      "name": "top_n",
      "type": "integer",
      "description": "Number of top pages to return, ranked by the selected metric. Default: 10. Max: 50.",
      "required": false
    },
    {
      "name": "page_filter",
      "type": "string",
      "description": "Optional filter to limit results to pages containing this string. Example: '/products' would match '/products', '/products/shoes', etc.",
      "required": false
    }
  ],
  "invocation": {
    "url": "https://your-railway-url.up.railway.app/tools/traffic",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

**Important Opal Manifest Notes (from Test Readiness Analyzer learnings):**

- The `description` field is critical — Opal uses it to decide when to invoke your tool
- Parameter descriptions should include examples of valid values
- Opal sends parameters in the request body as JSON
- Opal may send parameters as strings even if typed as integer — always coerce
- Include sensible defaults so the tool works even with minimal input

---

#### D. `app/analytics/client.py` — Adobe Analytics API Client

**Base URL:** `https://analytics.adobe.io`

**Required Headers for All Requests:**

```
Authorization: Bearer {access_token}
x-api-key: {CLIENT_ID}
x-proxy-global-company-id: {COMPANY_ID}
Content-Type: application/json
```

**Primary Endpoint — Reports:**

```
POST https://analytics.adobe.io/api/{COMPANY_ID}/reports
```

**Example Report Request Body:**

```json
{
  "rsid": "your_report_suite_id",
  "globalFilters": [
    {
      "type": "dateRange",
      "dateRange": "2026-02-01T00:00:00.000/2026-02-15T00:00:00.000"
    }
  ],
  "metricContainer": {
    "metrics": [
      {
        "columnId": "0",
        "id": "metrics/pageviews"
      }
    ]
  },
  "dimension": "variables/page",
  "settings": {
    "countRepeatInstances": true,
    "limit": 10,
    "page": 0,
    "nonesBehavior": "return-nones"
  }
}
```

**Example Report Response:**

```json
{
  "totalPages": 1,
  "firstPage": true,
  "lastPage": true,
  "numberOfElements": 10,
  "number": 0,
  "totalElements": 150,
  "columns": {
    "dimension": {
      "id": "variables/page",
      "type": "string"
    },
    "columnIds": ["0"]
  },
  "rows": [
    {
      "itemId": "1234567890",
      "value": "/home",
      "data": [12450.0]
    },
    {
      "itemId": "1234567891",
      "value": "/products",
      "data": [8230.0]
    }
  ],
  "summaryData": {
    "filteredTotals": [45670.0],
    "totals": [45670.0]
  }
}
```

**Adding a Segment Filter:**

```json
{
  "rsid": "your_report_suite_id",
  "globalFilters": [
    {
      "type": "dateRange",
      "dateRange": "2026-02-01T00:00:00.000/2026-02-15T00:00:00.000"
    },
    {
      "type": "segment",
      "segmentId": "s300000000_0000000000000000000"
    }
  ],
  "metricContainer": { ... },
  "dimension": "variables/page",
  "settings": { ... }
}
```

**Segments Endpoint (to list available segments):**

```
GET https://analytics.adobe.io/api/{COMPANY_ID}/segments?rsid={REPORT_SUITE_ID}&limit=50
```

---

#### E. `app/analytics/query_builder.py` — Query Builder

Translates tool parameters into Adobe Analytics API request bodies.

**Responsibilities:**

- Map metric names ("pageviews", "occurrences") to Adobe IDs ("metrics/pageviews", "metrics/occurrences")
- Map dimension names ("page", "referrer type") to Adobe IDs ("variables/page", "variables/referrertype")
- Convert parsed date ranges to ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000/YYYY-MM-DDTHH:MM:SS.000)
- Apply segment filters when specified
- Set pagination and sort parameters
- Handle page-name filtering using search/clause in the request

**Page Name Filtering:**

```json
{
  "settings": {
    "limit": 10,
    "page": 0
  },
  "search": {
    "clause": "( CONTAINS '/products' )"
  }
}
```

---

#### F. `app/analytics/response_parser.py` — Response Parser

Transforms Adobe's JSON response into clean, structured data for the tool layer.

**Output Structure:**

```python
@dataclass
class AnalyticsResult:
    rows: list[dict]          # [{"dimension_value": "/home", "metrics": {"pageviews": 12450}}]
    totals: dict              # {"pageviews": 45670}
    date_range: str           # "Feb 1–15, 2026"
    dimension_name: str       # "Page"
    metric_names: list[str]   # ["Page Views"]
    row_count: int            # 10
    total_available: int      # 150
```

---

#### G. `app/utils/date_parser.py` — Date Range Parser

Converts natural language date references to Adobe's ISO 8601 date range format.

**Supported Patterns:**

| Input | Output |
|-------|--------|
| "last 7 days" | Rolling 7 days ending yesterday |
| "last week" | Monday–Sunday of prior week |
| "this week" | Monday–today |
| "last month" | Full prior calendar month |
| "this month" | 1st of current month–today |
| "last 30 days" | Rolling 30 days ending yesterday |
| "last 90 days" | Rolling 90 days ending yesterday |
| "February 2026" | Feb 1–Feb 28/29 |
| "Q1 2026" | Jan 1–Mar 31 |
| Default | Last 7 days |

**Output Format:** `"YYYY-MM-DDTHH:MM:SS.000/YYYY-MM-DDTHH:MM:SS.000"`

Use `python-dateutil` for relative date calculations. All dates in UTC.

---

#### H. `app/utils/formatters.py` — Response Formatters

Format the parsed analytics data into readable text for Opal responses.

**Formatting Rules:**

- Numbers with commas (12,450 not 12450)
- Percentages to 1 decimal place (42.3%)
- Date ranges in human-readable format (Feb 1–15, 2026)
- Tables using fixed-width alignment for comparison views
- Always include totals where applicable
- Include context about what was queried ("Top 10 pages by page views, last 7 days")

---

## 5. Opal Integration

### Tool Registration

1. Deploy to Railway and get the public URL
2. In Optimizely Opal admin → Tools → Add Custom Tool
3. Enter discovery URL: `https://your-app.up.railway.app/discovery`
4. Click "Sync" to pull the manifest
5. Verify all 5 tools appear with correct descriptions

### Agent Configuration

Create a dedicated Opal agent (or add to an existing one):

**Agent Name:** Adobe Analytics Assistant

**Agent Instructions:**

```
You help users explore their Adobe Analytics data through natural language.
You have access to tools that query Adobe Analytics for page-level traffic
data, referrer breakdowns, and segment comparisons.

When users ask about traffic, page views, or website performance, use the
appropriate Adobe Analytics tool. Always specify reasonable defaults if
the user doesn't provide a date range (default to last 7 days).

Available data includes:
- Page views and occurrences by page name
- Traffic breakdown by referrer type (Direct, Organic Search, etc.)
- Basic segments: Mobile, Desktop, Tablet, New Visitors, Return Visitors
- Day-level date granularity

Data NOT available (do not attempt these queries):
- Revenue or conversion data
- Custom dimensions (eVars, props)
- Product data
- Campaign tracking

If a user asks for data you cannot retrieve, explain what IS available
and suggest an alternative query.
```

### Instruction Configuration

Add an Opal Instruction to guide tool selection:

**Instruction Name:** Adobe Analytics Data Access

**Instruction Text:**

```
When users ask about website traffic, page performance, visitor sources,
or analytics data, use the Adobe Analytics tools to retrieve real data.
Do not guess or estimate — always query the actual data.
```

---

## 6. Environment Variables

### Required for Railway

```env
# Adobe Analytics OAuth
ADOBE_CLIENT_ID=a86d9fb26d054419b84abc384bb8f1fd
ADOBE_CLIENT_SECRET=your_client_secret
ADOBE_ORG_ID=DCF77919596885950A495D3E@AdobeOrg
ADOBE_COMPANY_ID=exchane5
ADOBE_REPORT_SUITE_ID=33sticksjennwebprops

# Opal Integration
OPAL_BEARER_TOKEN=your_opal_tool_token

# App Config
PORT=8000
ENVIRONMENT=production
LOG_LEVEL=info
```

---

## 7. Dependencies

### `requirements.txt`

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
python-dateutil==2.8.2
python-dotenv==1.0.0
pydantic==2.5.3
```

**Why these choices:**

- `httpx` over `requests` — async-native HTTP client, works with FastAPI's async
- `python-dateutil` — robust relative date parsing
- `pydantic` — request/response validation (already a FastAPI dependency)

### `Procfile` (Railway)

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 8. Error Handling Strategy

### Adobe API Errors

| Status | Meaning | Tool Response |
|--------|---------|---------------|
| 401 | Token expired | Auto-refresh and retry once |
| 403 | Insufficient permissions | "Unable to access this report suite. Check permissions." |
| 429 | Rate limited | Wait and retry with backoff (max 3 attempts) |
| 400 | Bad request | Log the request, return "Invalid query parameters" with details |
| 500+ | Adobe outage | "Adobe Analytics is temporarily unavailable. Try again shortly." |

### Opal-Side Error Responses

Always return valid JSON, even on errors:

```json
{
  "status": "error",
  "message": "Unable to retrieve data: Adobe Analytics returned a 403 error. The service account may not have access to the requested report suite.",
  "suggestion": "Verify that the service account has been granted access in Adobe Admin Console."
}
```

---

## 9. Sprint Plan

### Sprint 1 (Week 1): Foundation

- [ ] Project scaffold (directory structure, config, dependencies)
- [ ] Adobe OAuth token management (`adobe_auth.py`)
- [ ] Basic Adobe Analytics API client (`client.py`)
- [ ] Health check and discovery endpoints
- [ ] Manual testing: verify token acquisition and a basic report query
- [ ] Deploy to Railway with env vars configured

### Sprint 2 (Week 2): Core Tools

- [ ] Date range parser with tests
- [ ] Query builder with tests
- [ ] Response parser with tests
- [ ] UC1: Traffic Analysis tool (end-to-end)
- [ ] UC2: Referrer Breakdown tool (end-to-end)
- [ ] Register tools in Opal and test via Chat

### Sprint 3 (Week 3): Advanced Tools

- [ ] UC3: Page Comparison tool (period-over-period logic)
- [ ] UC4: Segment Insights tool (segment ID mapping)
- [ ] UC5: Traffic Validation tool (daily stats + assessment)
- [ ] Response formatting polish
- [ ] Error handling hardening

### Sprint 4 (Week 4): Polish & Demo

- [ ] Agent and instruction configuration in Opal
- [ ] End-to-end testing of all 5 use cases
- [ ] Demo script preparation
- [ ] Documentation for handoff / presentation
- [ ] Edge case handling (empty results, single-page sites, etc.)

---

## 10. Testing Strategy

### Unit Tests

- `test_date_parser.py` — All date range patterns produce correct ISO ranges
- `test_query_builder.py` — Parameters correctly translate to Adobe API request format
- `test_response_parser.py` — Adobe responses correctly parsed into clean structures

### Integration Tests (with mocked Adobe API)

- Each tool endpoint returns expected format given mocked API responses
- Error scenarios (401, 403, 429, 500) handled gracefully
- Token refresh flow works correctly

### End-to-End Tests (manual, via Opal Chat)

- Each use case query produces accurate, well-formatted results
- Opal correctly selects the right tool for different query types
- Edge cases: no data returned, very large result sets, ambiguous date ranges