"""
Docs: https://www.bls.gov/developers/api_faqs.htm
Series IDs can be found at https://www.bls.gov/help/hlpforma.htm
"""

import json
import logging
import requests

series_id_map = {
    "CUUR0000SA0":          "Consumer Price Index - All Urban Consumers", # good
    "CUUR0000SA0L1E":       "Consumer Price Index - All Urban Consumers (All items less food and energy)", # good
    "PCU22112222112241":    "Producer Price Index Industry Data - Current Series", # TBD
    "WPS141101":            "Producer Price Index Commodity Data - Current Series", # good
    "CEU0800000003":        "National Employment, Hours, and Earnings", # TBD
    "LNS14000000":          "Unemployment rate", # good
}

API_BASE_URL = "https://api.bls.gov/publicAPI"
headers = {'Content-type': 'application/json'}

def _http_post(api_key: str, series_id: str, start_year: int, end_year: int):
    data = {
        "seriesid": [series_id],
        "startyear": start_year,
        "endyear": end_year,
        "registrationkey": api_key
    }

    res = requests.post(f"{API_BASE_URL}/v2/timeseries/data/", data=json.dumps(data), headers=headers, timeout=120)

    if res.status_code != 200:
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return res.json()

def get_series_data(api_key: str, series_id: str, start_year: int, end_year: int):
    """Get the BLS data for the specified series.

    Args:
        api_key (str): API key to use in the request
        series_id (str): BLS data series ID
        start_year (int): start year of the data to fetch
        end_year (int): end year of the data to fetch

    Returns:
        json: response in json form
    """
    logging.info(f"Getting ({series_id}) {series_id_map[series_id]} for years {start_year}-{end_year}")

    return _http_post(api_key, series_id, start_year, end_year)
