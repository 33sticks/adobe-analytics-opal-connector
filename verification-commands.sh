# Adobe Analytics API - Verification Commands
# Pre-populated with your credentials. Fill in the 3 placeholder values marked with YOUR_

# ============================================================
# STEP A: Get an Access Token
# ============================================================
# Replace YOUR_CLIENT_SECRET with your secret from Adobe Developer Console

curl -X POST "https://ims-na1.adobelogin.com/ims/token/v3" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=a86d9fb26d054419b84abc384bb8f1fd&client_secret=YOUR_CLIENT_SECRET&scope=openid,AdobeID,additional_info.projectedProductContext"

# Expected response:
# {
#   "access_token": "eyJ...(long string)",
#   "token_type": "bearer",
#   "expires_in": 86399
# }


# ============================================================
# STEP B: Test a Basic Report
# ============================================================
# Replace:
#   YOUR_ACCESS_TOKEN  → access_token from Step A
#   YOUR_COMPANY_ID    → Global Company ID from AA Admin → Company Settings → API Access
#   YOUR_REPORT_SUITE  → Report Suite ID from AA Admin → Report Suites

curl -X POST "https://analytics.adobe.io/api/YOUR_COMPANY_ID/reports" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "x-api-key: a86d9fb26d054419b84abc384bb8f1fd" \
  -H "x-proxy-global-company-id: YOUR_COMPANY_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "rsid": "YOUR_REPORT_SUITE",
    "globalFilters": [
      {
        "type": "dateRange",
        "dateRange": "2026-02-01T00:00:00.000/2026-02-22T00:00:00.000"
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
      "limit": 5,
      "page": 0
    }
  }'

# Expected response: JSON with "rows" array containing page names and pageview counts


# ============================================================
# STEP C (Optional): List Available Segments
# ============================================================
# This will show you the segment IDs we need for Use Case 4

curl -X GET "https://analytics.adobe.io/api/YOUR_COMPANY_ID/segments?rsid=YOUR_REPORT_SUITE&limit=50&includeType=shared,all" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "x-api-key: a86d9fb26d054419b84abc384bb8f1fd" \
  -H "x-proxy-global-company-id: YOUR_COMPANY_ID"

# Expected response: JSON array of segment objects with "id", "name", "description"


# ============================================================
# REMAINING VALUES TO COLLECT
# ============================================================
# All values collected! Only the client secret remains private.
#
# ✅ Client ID:       a86d9fb26d054419b84abc384bb8f1fd
# ✅ Org ID:          DCF77919596885950A495D3E@AdobeOrg
# 🔒 Client Secret:   (keep private, enter in Railway env vars only)
# ✅ Company ID:      exchane5
# ✅ Report Suite ID: 33sticksjennwebprops
