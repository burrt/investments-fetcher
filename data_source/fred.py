"""
Docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""

import requests

API_BASE_URL = "https://api.stlouisfed.org"

series_id_map = {
    # https://fred.stlouisfed.org/series/UMCSENT
    "UMCSENT": "University of Michigan: Consumer Sentiment",
    # https://fred.stlouisfed.org/series/PERMIT
    "PERMIT": "New Privately-Owned Housing Units Authorized in Permit-Issuing Places: Total Units",
}

def get_series_data(api_key: str, series_id: str, start_date: str, end_date: str, freq: str):
    params = {
        "api_key": api_key,
        "series_id": series_id,
        "realtime_start": start_date,
        "realtime_end": end_date,
        "frequency": freq,
        "sort_order": "desc",
        "file_type": "json"
    }

    res = requests.get(f"{API_BASE_URL}/fred/series/observations", params=params, timeout=120)

    if res.status_code != 200:
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return res.json(), series_id_map[series_id]
