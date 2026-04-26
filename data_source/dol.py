"""
Department of Labor
Docs: https://dataportal.dol.gov/api-examples
"""

import json
import logging
import os
import requests

API_BASE_URL = "https://apiprod.dol.gov"

def get_unemployment_weekly_claims(api_key: str):
    """Get Insurance National Weekly Claims - https://dataportal.dol.gov/datasets/10281

    Args:
        api_key (str): DOL API key to use

    Returns:
        json: response in json form
    """

    params = {"X-API-KEY": api_key, "sort": "desc", "sort_by": "rptdate", "limit": "1"}

    url = f"{API_BASE_URL}/v4/get/ETA/ui_national_weekly_claims/json"
    res = requests.get(url, params=params, timeout=120)
    payload = res.json()

    if os.getenv("SKIP_LOCAL_DEBUG_PAYLOAD") == "false":
        with open("payload.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    if res.status_code != 200:
        logging.error(f"Failed to fetch data from DOL API {url}: {payload}")
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return payload, "Insurance National Weekly Claims"
