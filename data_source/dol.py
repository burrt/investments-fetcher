"""
Department of Labor
Docs: https://dataportal.dol.gov/api-examples
"""

API_BASE_URL = "https://apiprod.dol.gov"

import logging
import requests

def get_unemployment_weekly_claims(api_key: str):
    """Get Insurance National Weekly Claims - https://dataportal.dol.gov/datasets/10281

    Args:
        api_key (str): DOL API key to use

    Returns:
        json: response in json form
    """

    params = {"X-API-KEY": api_key, "sort": "desc", "limit": "1"}
    res = requests.get(f"{API_BASE_URL}/v4/get/ETA/ui_national_weekly_claims/json", params=params, timeout=120)
    return res.json(), "Insurance National Weekly Claims"

