"""
Docs: https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf
"""

import logging
import requests

gdp_table_id_map = {
    # GDP series code: A191RL
    "T10101": "(Table 1. Real Gross Domestic Product and Related Measures: Percent Change from Preceding Period)",
    "T10102": "(Table 2. Contributions to Percent Change in Real Gross Domestic Product)",
    "T10103": "(Table 3. Gross Domestic Product: Level and Change from Preceding Period)",
    "T10104": "(Table 4. Price Indexes for Gross Domestic Product and Related Measures: Percent Change from Preceding Period)",
    "T10105": "(Table 5. Real Gross Domestic Product: Annual Percent Change)",

    # nice to have
    "T10106": "(Table 6. Real Gross Domestic Product: Percent Change from Quarter One Year Ago)",
    "T10107": "(Table 7. Relation of Gross Domestic Product, Gross National Product, and National Income)",
    "T10108": "(Table 8. Personal Income and Its Disposition)",
}

API_BASE_URL = "https://apps.bea.gov"

def get_gdp(api_key: str, table_id: str, year: int, freq="Q"):
    """Get the GDP data for the given ID.

    Args:
        api_key (str): BEA API key to use
        table_id (str): GDP table ID
        year (int): GDP year to fetch
        freq (str, optional): frequency of GDP interval. Defaults to "Q" i.e. quarterly

    Raises:
        RuntimeError: for non-successful status code

    Returns:
        json: response in json form
    """

    # Appendix B – NIPA (National Income and Product Accounts)
    data_set_name = "NIPA"

    logging.info(f"Getting {gdp_table_id_map[table_id]}, table ID: ({table_id}) for year {year}")

    params = {
        "UserID": api_key,
        "method": "GetData",
        "DataSetName": data_set_name,
        "Year": year,
        "Industry": "ALL",
        "TableName": table_id,
        "Frequency": freq,
        "ResultFormat": "JSON",
    }
    res = requests.get(f"{API_BASE_URL}/api/data", params=params, timeout=120)

    if res.status_code != 200:
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return res.json()["BEAAPI"]["Results"]["Data"][-1], gdp_table_id_map[table_id]

def get_all_gdp(year: int, freq="Q"):
    """Get all the GDP data for the specified year.

    Args:
        year (int): year to fetch
        freq (str, optional): GDP granularity. Defaults to "Q" i.e. quarterly.
    """
    for table_id in gdp_table_id_map:
        return
        # TODO: fix
        # get_gdp(table_id, year, freq)
