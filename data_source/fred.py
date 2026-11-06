"""
Fetch FRED observations and attach a series-specific display name.

Catalogue, units, native frequencies, source links and open TODOs: docs/fred.md.
Definitions checked against FRED series pages on 2026-11-06. For each ID, inspect
https://fred.stlouisfed.org/series/<ID>; its source, units, frequency, seasonal
adjustment and notes determine what the observations mean.

API references:
- Observations: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- Metadata: https://fred.stlouisfed.org/docs/api/fred/series.html
- Vintages: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

This adapter returns the API payload without calculating changes. Its frequency
parameter requests aggregation, not seasonal adjustment. Current caller defaults
can change native frequency; see the TODO in get_series_data and docs/fred.md.
No vintage is selected, so historical observations reflect information available
today, including revisions.
"""

import json
import logging
import os
import requests

API_BASE_URL = "https://api.stlouisfed.org"

# Preserve each ID's actual scope; alternatives for other measures are in docs/fred.md.
series_id_map = {
    "UMCSENT":      "University of Michigan: Consumer Sentiment",
    "PERMIT":       "New Privately-Owned Housing Units Authorized in Permit-Issuing Places: Total Units",
    "HOUST":        "New Privately-Owned Housing Units Started: Total Units",
    "COMPU1USA":    "New Privately-Owned Housing Units Completed: Single-Family Units",
    "ICSA":         "Initial Unemployment Insurance Claims",
    "CCSA":         "Continued Claims (Insured Unemployment)",
    "MICH":         "University of Michigan: Inflation Expectation (Median, Next 12 Months)",
    "RSXFS":        "Advance Retail Sales: Retail Trade (Excluding Food Services)",
    "DGORDER":      "Manufacturers' New Orders: Durable Goods",
    "ACDGNO":       "Manufacturers' New Orders: Consumer Durable Goods",
    "DPI":          "Disposable Personal Income (Nominal)",
    "IEABC":        "Balance on Current Account",
    "IEABCP":       "Balance on Capital Account",
    "PCE":          "Personal Consumption Expenditures (Nominal Spending)",
}

def get_series_data(api_key: str, series_id: str, start_date: str, end_date: str, freq: str, *, timeout: int):
    """Return observations within the requested observation-date range and a label.

    Dates are YYYY-MM-DD observation dates, not publication dates. ``freq`` is
    currently required and forwarded to FRED; coarser frequencies use the API's
    default averaging method. No units transformation or vintage is requested.
    """
    # TODO: Make freq optional and omit the API parameter for native observations;
    # coordinate with both CLI and Lambda defaults in fetcher.py. Add explicit
    # aggregation selection and validate it against native metadata. See docs/fred.md.
    # TODO: Track request settings and retrieval/vintage metadata alongside the raw
    # payload; validate missing values, completeness and period coverage before any
    # future summaries. The detailed follow-up checklist is in docs/fred.md.
    params = {
        "api_key": api_key,
        "series_id": series_id,
        "observation_start": start_date,
        "observation_end": end_date,
        "frequency": freq,
        "sort_order": "desc",
        "file_type": "json"
    }

    url = f"{API_BASE_URL}/fred/series/observations"
    res = requests.get(url, params=params, timeout=timeout)
    payload = res.json()

    if os.getenv("SKIP_LOCAL_DEBUG_PAYLOAD") == "false":
        with open("payload.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    if res.status_code != 200:
        logging.error("Failed to fetch data from FRED API %s: %s", url, payload)
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return payload, series_id_map[series_id]
