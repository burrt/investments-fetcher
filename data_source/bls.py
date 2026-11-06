"""
Docs: https://www.bls.gov/developers/api_faqs.htm
Series ID formats and code lists: https://www.bls.gov/help/hlpforma.htm
Organisation name: Wall St Bumpkin

CPI-U mappings below cover the U.S. city average, with monthly index levels (1982-84=100).
BLS uses seasonally adjusted (SA) indexes for the conventional
monthly headline changes and not seasonally adjusted (NSA) indexes for headline
12-month changes.
Retain both variants; the IDs identify indexes, not growth rates.
The current summary function still applies a generic monthly calculation; see TODO.

Official mapping sources:
- ID structure (third character: S = SA, U = NSA):
  https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm
- All items, NSA / SA:
  https://data.bls.gov/timeseries/CUUR0000SA0
  https://data.bls.gov/timeseries/CUSR0000SA0
- All items less food and energy, NSA / SA:
  https://data.bls.gov/timeseries/CUUR0000SA0L1E
  https://data.bls.gov/timeseries/CUSR0000SA0L1E
- Monthly versus 12-month reporting convention (Table A):
  https://www.bls.gov/news.release/cpi.nr0.htm
"""

import json
import logging
import os
import requests
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

series_id_map = {
    "CUUR0000SA0":          "Consumer Price Index - All Urban Consumers (All items, not seasonally adjusted)",
    "CUSR0000SA0":          "Consumer Price Index - All Urban Consumers (All items, seasonally adjusted)",
    "CUUR0000SA0L1E":       "Consumer Price Index - All Urban Consumers (All items less food and energy, not seasonally adjusted)",
    "CUSR0000SA0L1E":       "Consumer Price Index - All Urban Consumers (All items less food and energy, seasonally adjusted)",

    "CES0000000001":        "National Employment, Hours, and Earnings", # good - https://www.bls.gov/news.release/empsit.t17.htm
    "LNS14000000":          "Unemployment rate", # good
    "WPSFD4":               "United States Producer Price Inflation MoM", # good

    "PCU22112222112241":    "Producer Price Index - Residential Electric Power (not seasonally adjusted)",
    "WPS141101":            "Producer Price Index Commodity Data - Current Series", # good
}

API_BASE_URL = "https://api.bls.gov/publicAPI"
headers = {'Content-type': 'application/json'}

def _http_post(api_key: str, series_id: str, start_year: int, end_year: int, *, timeout: int):
    data = {
        "seriesid": [series_id],
        "startyear": start_year,
        "endyear": end_year,
        "registrationkey": api_key
    }

    url = f"{API_BASE_URL}/v2/timeseries/data/"
    res = requests.post(url, data=json.dumps(data), headers=headers, timeout=timeout)
    payload = res.json()

    if os.getenv("SKIP_LOCAL_DEBUG_PAYLOAD") == "false":
        with open("payload.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    if res.status_code != 200:
        logging.error(f"Failed to fetch data from BLS API {url}: {payload}")
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return payload, series_id_map[series_id], filter_data_to_latest_datapoint(payload)

def filter_data_to_latest_datapoint(json):
    # TODO: Replace the generic first-two-records / mom_percent summary with
    # series-aware period selection and calculations:
    # - Select monthly records (M01-M12) by year and period; exclude annual and
    #   half-year summaries, and handle missing/insufficient observations explicitly.
    # - Match the previous calendar month for MoM or the same month a year earlier
    #   for YoY; fetch prior-year data when needed, including January comparisons.
    # - Use SA CPI for headline MoM and NSA CPI for headline YoY. Payrolls need
    #   absolute changes (source units: thousands of jobs); unemployment needs
    #   percentage-point changes. Preserve both periods and label each result.
    # - Verify year boundaries, gaps and short responses, then reconcile calculations
    #   with dated official tables using the same vintage and reporting precision.
    series = json["Results"]["series"][0]["data"]

    latest = series[0]
    previous = series[1]

    latest_raw = latest.get("value")
    previous_raw = previous.get("value")

    try:
        latest_value = Decimal(latest_raw)
        previous_value = Decimal(previous_raw)
    except InvalidOperation as ex:
        raise RuntimeError(
            f"Unable to parse BLS values as decimals: latest={latest_raw}, previous={previous_raw}"
        ) from ex

    latest_value = Decimal(latest["value"])
    previous_value = Decimal(previous["value"])

    mom_percent = (
        ((latest_value - previous_value) / previous_value) * Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "year": int(latest["year"]),
        "period_name": latest["periodName"],
        "latest_value": float(latest_value),
        "previous_value": float(previous_value),
        "text": latest.get("footnotes", [{}])[0].get("text", ""),
        "mom_percent": float(mom_percent),
    }

def get_series_data(api_key: str, series_id: str, start_year: int, end_year: int, *, timeout: int):
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

    return _http_post(api_key, series_id, start_year, end_year, timeout=timeout)
