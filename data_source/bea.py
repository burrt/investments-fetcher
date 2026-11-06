"""BEA NIPA GDP tables, not the numbered tables in a GDP press release.

Mappings and GDP SeriesCode values checked against the live BEA API on 2026-11-06:
GetParameterValues(DataSetName=NIPA, ParameterName=TableName), then GetData for
each table. See docs/bea.md for the complete catalogue, units and follow-up TODOs.

Start with get_gdp for the request flow and filter_data_to_latest_datapoint for
the summary. The private helpers below handle each step in those flows.

T10101 / NIPA 1.1.1 / A191RL with Frequency=Q supplies the conventional headline:
real GDP percent change from the preceding quarter, seasonally adjusted at an
annual rate. Use BEA's published change directly; do not annualize it again.
Frequency=A instead compares calendar-year levels. Neither is quarterly YoY.

The GDP row's METRIC_NAME, CL_UNIT and UNIT_MULT determine its measurement and
scale. In particular, dollar DataValues can be in millions even when the table
title says billions. Source notes retain the index/chained-dollar reference year.

Official references:
- API guide, Appendix B (NIPA):
  https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf
- Headline GDP and release links: https://www.bea.gov/data/gdp/gross-domestic-product
- Annualization: https://www.bea.gov/help/faq/122
"""

import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation

import requests

API_BASE_URL = "https://apps.bea.gov"

gdp_table_id_map = {
    "T10101": "NIPA Table 1.1.1. Percent Change From Preceding Period in Real Gross Domestic Product",
    "T10102": "NIPA Table 1.1.2. Contributions to Percent Change in Real Gross Domestic Product",
    "T10103": "NIPA Table 1.1.3. Real Gross Domestic Product, Quantity Indexes",
    "T10104": "NIPA Table 1.1.4. Price Indexes for Gross Domestic Product",
    "T10105": "NIPA Table 1.1.5. Gross Domestic Product",
    "T10106": "NIPA Table 1.1.6. Real Gross Domestic Product, Chained Dollars",
    "T10107": "NIPA Table 1.1.7. Percent Change From Preceding Period in Prices for Gross Domestic Product",
    "T10108": "NIPA Table 1.1.8. Contributions to Percent Change in the Gross Domestic Product Price Index",
}

# GDP is line 1 in each table. Contribution tables repeat the aggregate growth
# series; their component rows have different codes and percentage-point units.
GDP_SERIES_CODES = {
    "T10101": "A191RL",
    "T10102": "A191RL",
    "T10103": "A191RA",
    "T10104": "A191RG",
    "T10105": "A191RC",
    "T10106": "A191RX",
    "T10107": "A191RV",
    "T10108": "A191RV",
}
PERCENT_CHANGE_TABLES = {"T10101", "T10102", "T10107", "T10108"}
DOLLAR_LEVEL_TABLES = {"T10105", "T10106"}


def get_gdp(api_key: str, table_id: str, year: int | str, freq="Q", *, timeout: int):
    """Return (payload, NIPA table label, latest GDP summary) for one frequency.

    Year accepts BEA's year or comma-separated years. The CLI currently passes
    only its start year; see the date-range TODO in fetcher.py. All observations
    and notes are retained, but the echoed request credential is redacted.
    Raises ValueError for unsupported selections, RuntimeError for failed or
    unusable responses. This function does not post to Slack or upload to S3.
    """
    frequency = _validate_table_and_frequency(table_id, freq)
    table_name = gdp_table_id_map[table_id]

    logging.info("Getting %s, table ID: (%s) for year %s", table_name, table_id, year)

    payload = _http_get(api_key, table_id, year, frequency, timeout=timeout)
    _redact_api_key(payload)
    latest_gdp_summary = filter_data_to_latest_datapoint(payload, table_id, frequency)

    if os.getenv("SKIP_LOCAL_DEBUG_PAYLOAD") == "false":
        with open("payload.json", "w", encoding="utf-8") as debug_file:
            json.dump(payload, debug_file, indent=2, ensure_ascii=False)

    return payload, table_name, latest_gdp_summary


def get_all_gdp(api_key: str, year: int | str, freq="Q", *, timeout: int):
    """Fetch all eight tables; return {table_id: (payload, label, summary)}.

    Each call uses the same year, frequency, API key and HTTP timeout. Like
    get_gdp, this helper only fetches data; it does not publish the results.
    """
    results_by_table = {}
    for table_id in gdp_table_id_map:
        results_by_table[table_id] = get_gdp(api_key, table_id, year, freq, timeout=timeout)
    return results_by_table


def filter_data_to_latest_datapoint(payload, table_id, freq="Q"):
    """Summarize GDP within the returned years, preserving source value/scale.

    Select by table, GDP SeriesCode and line, not an English description. Annual
    and quarterly observations cannot compete for 'latest'. Fail on an unusable
    latest value instead of silently falling back to an older observation.
    """
    frequency = _validate_table_and_frequency(table_id, freq)
    api_response = payload.get("BEAAPI", {})
    results = api_response.get("Results", {})
    if "Error" in api_response or "Error" in results:
        raise RuntimeError(
            "BEA API returned an error; check credentials, parameters and data availability"
        )

    observations = results.get("Data", [])
    latest_observation = _find_latest_gdp_observation(observations, table_id, frequency)
    metric_name, calculation_type, unit_multiplier = _read_gdp_measurement(
        latest_observation, table_id
    )
    measurement_basis = _describe_measurement_basis(table_id, frequency)
    source_notes = _get_source_notes(latest_observation, results.get("Notes", []))

    # TODO: Add retrieval time, release/vintage provenance and revision detection;
    # UTCProductionTime and a table's LastRevised note are not observation vintages.
    return {
        "period": latest_observation["TimePeriod"],
        "frequency": frequency,
        "series_code": latest_observation["SeriesCode"],
        "value": latest_observation["DataValue"],
        "metric": metric_name,
        "calculation": calculation_type,
        "unit_multiplier": unit_multiplier,
        "basis": measurement_basis,
        "source_notes": source_notes,
    }


def _validate_table_and_frequency(table_id: str, frequency: str):
    """Check the table is supported and return its frequency in uppercase."""
    if table_id not in gdp_table_id_map:
        raise ValueError(f"Unsupported BEA NIPA table: {table_id}")

    frequency = frequency.upper()
    if frequency not in {"A", "Q"}:
        raise ValueError("BEA GDP summary requires one frequency: Q or A")
    return frequency


def _http_get(api_key: str, table_id: str, year: int | str, frequency: str, *, timeout: int):
    """Request one NIPA table and decode the JSON response."""
    params = {
        "UserID": api_key,
        "method": "GetData",
        "DataSetName": "NIPA",
        "Year": year,
        "TableName": table_id,
        "Frequency": frequency,
        "ResultFormat": "JSON",
    }
    url = f"{API_BASE_URL}/api/data"
    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException:
        # requests exceptions can include the full URL, including UserID.
        raise RuntimeError("BEA HTTP request failed") from None
    if response.status_code != 200:
        raise RuntimeError(f"Unexpected BEA HTTP status code: {response.status_code}")

    try:
        return response.json()
    except ValueError:
        raise RuntimeError("BEA returned an invalid JSON response") from None


def _redact_api_key(payload):
    """Replace the echoed UserID in place before the payload is logged or saved."""
    api_response = payload.get("BEAAPI", {})
    request_details = api_response.get("Request", {})
    request_parameters = request_details.get("RequestParam", [])

    for parameter in request_parameters:
        if parameter.get("ParameterName", "").upper() == "USERID":
            parameter["ParameterValue"] = "[REDACTED]"


def _find_latest_gdp_observation(observations, table_id, frequency):
    """Find a single latest GDP row for the requested table and frequency."""
    expected_series_code = GDP_SERIES_CODES[table_id]
    gdp_observations = []

    for observation in observations:
        if observation.get("TableName") != table_id:
            continue
        if observation.get("SeriesCode") != expected_series_code:
            continue
        if str(observation.get("LineNumber")) != "1":
            continue

        # BEA uses YYYY for annual data and YYYYQ1 through YYYYQ4 for quarters.
        observation_period = observation.get("TimePeriod", "")
        if not re.fullmatch(r"\d{4}(?:Q[1-4])?", observation_period):
            raise RuntimeError(f"BEA returned an invalid GDP period for {table_id}")

        observation_frequency = "Q" if "Q" in observation_period else "A"
        if observation_frequency == frequency:
            gdp_observations.append(observation)

    if not gdp_observations:
        raise RuntimeError(
            f"BEA returned no GDP observations for {table_id} at frequency {frequency}"
        )

    # Within one frequency, these period strings sort in chronological order.
    latest_period = max(observation["TimePeriod"] for observation in gdp_observations)
    latest_observations = [
        observation for observation in gdp_observations
        if observation["TimePeriod"] == latest_period
    ]
    if len(latest_observations) != 1:
        raise RuntimeError(f"BEA returned duplicate latest GDP observations for {table_id}")
    return latest_observations[0]


def _read_gdp_measurement(observation, table_id):
    """Validate the value; return (metric name, calculation type, scale exponent).

    The decimal is only used for validation. The summary keeps BEA's original
    formatted value, and UNIT_MULT describes its scale (for example, 6 = millions).
    """
    try:
        raw_value = observation["DataValue"]
        numeric_value = Decimal(str(raw_value).replace(",", ""))
        if not numeric_value.is_finite():
            raise ValueError

        unit_multiplier = int(observation["UNIT_MULT"])
        # Live responses use METRIC_NAME; the API guide also lists Metric_Name.
        metric_name = observation.get("METRIC_NAME") or observation["Metric_Name"]
        calculation_type = observation["CL_UNIT"]
    except (KeyError, ValueError, InvalidOperation, TypeError):
        raise RuntimeError(
            f"BEA latest GDP value or units are unavailable for {table_id}"
        ) from None
    return metric_name, calculation_type, unit_multiplier


def _describe_measurement_basis(table_id, frequency):
    """Explain whether the value is growth, a dollar level or an index level."""
    if table_id in PERCENT_CHANGE_TABLES:
        if frequency == "Q":
            return "Change from preceding quarter, seasonally adjusted annual rate"
        return "Change from previous calendar year"

    if table_id in DOLLAR_LEVEL_TABLES:
        if frequency == "Q":
            return "Level, seasonally adjusted annual rate"
        return "Calendar-year level"

    if frequency == "Q":
        return "Seasonally adjusted index"
    return "Calendar-year index"


def _get_source_notes(observation, notes):
    """Keep only notes referenced by the selected observation's NoteRef field."""
    note_reference_text = observation.get("NoteRef", "")
    note_references = {reference.strip() for reference in note_reference_text.split(",")}
    return [note for note in notes if note.get("NoteRef") in note_references]
