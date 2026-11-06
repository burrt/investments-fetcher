"""
Department of Labor: Unemployment Insurance National Weekly Claims.

Catalogue and API definition verified on 2026-11-06:
- Dataset: https://dataportal.dol.gov/datasets/10305
- Metadata: https://apiprod.dol.gov/v4/datasets/10305
- API route/schema: https://apiprod.dol.gov/v4/dataset_documentation/10305
- Request examples: https://dataportal.dol.gov/api-examples

The catalogue ID identifies the dataset; retrieval uses the named endpoint
ETA/ui_national_weekly_claims. These are separate identifiers.

Field definitions from the dataset metadata:
- rptdate: week-ending observation date, not publication time.
- c4 / c5: initial claims, unadjusted / seasonally adjusted counts.
- c6 / c7: continued claims, unadjusted / seasonally adjusted counts.
- c8 / c9: four-week averages of seasonally adjusted initial / continued claims.

DOL warns that API updates lag publication by at least 30 minutes. The release
is available at https://www.dol.gov/ui/data.pdf. This adapter requests the latest
row by rptdate and returns the raw payload; it does not validate release freshness.
"""

import json
import logging
import os
import requests

API_BASE_URL = "https://apiprod.dol.gov"
DATASET_ID = "10305"
DATASET_NAME = "Unemployment Insurance National Weekly Claims"

def get_unemployment_weekly_claims(api_key: str, *, timeout: int):
    """Get the latest available national weekly-claims row from DOL.

    Args:
        api_key (str): DOL API key to use

    Returns:
        json: response in json form
    """

    params = {"X-API-KEY": api_key, "sort": "desc", "sort_by": "rptdate", "limit": "1"}

    url = f"{API_BASE_URL}/v4/get/ETA/ui_national_weekly_claims/json"
    res = requests.get(url, params=params, timeout=timeout)
    payload = res.json()

    if os.getenv("SKIP_LOCAL_DEBUG_PAYLOAD") == "false":
        with open("payload.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    if res.status_code != 200:
        logging.error("Failed to fetch data from DOL API %s: %s", url, payload)
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return payload, DATASET_NAME
