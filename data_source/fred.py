"""
Docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""

import logging
import requests

API_BASE_URL = "https://api.stlouisfed.org"

 # lookup: https://fred.stlouisfed.org/series/<code>
series_id_map = {
    "UMCSENT": "University of Michigan: Consumer Sentiment",
    "PERMIT": "New Privately-Owned Housing Units Authorized in Permit-Issuing Places: Total Units",
    "HOUST": "Housing Starts",
    "COMPU1USA": "Housing Completions",
    "ICSA": "Initial Jobless Claims",
    "CCSA": "Continuing Claims",
    "MICH": "USMCI: Inflation Expectations",
    "RSXFS": "Advanced Retail Sales",
    "DGORDER": "Durable Goods Orders",
    "ACDGNO": "New Orders: Total Manufacturing",
    "DPI": "Disposable Personal Income",
    "IEABC": "Capital Account (Quarterly)",
    "IEABCP": "Capital Account (CA) (Quarterly)",
    "PCE": "Personal Consumption Expenditure (PCE)",
}

def get_series_data(api_key: str, series_id: str, start_date: str, end_date: str, freq: str):
    params = {
        "api_key": api_key,
        "series_id": series_id,
        "observation_start": start_date,
        # "realtime_end": end_date, # defaults to 9999-12-31 (latest available)
        "frequency": freq,
        "sort_order": "desc",
        "file_type": "json"
    }

    url = f"{API_BASE_URL}/fred/series/observations"
    res = requests.get(url, params=params, timeout=120)

    if res.status_code != 200:
        logging.error(f"Failed to fetch data from FRED API {url}: {res.json()}")
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return res.json(), series_id_map[series_id]
