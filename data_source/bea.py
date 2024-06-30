"""
Docs: https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf
"""

import logging
import requests

gdp_table_id_map = {
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

api_base_url = "https://apps.bea.gov/api/data"

def gdp(api_key, table_id, year, freq="Q"):
    # Appendix B – NIPA (National Income and Product Accounts)
    data_set_name = "NIPA"

    logging.info(f"Getting GDP ({table_id}) for year {year}")

    res = requests.get(f"{api_base_url}?&UserID={api_key}&method=GetData&DataSetName={data_set_name}&Year={year}&Industry=ALL&TableName={table_id}&Frequency={freq}&ResultFormat=JSON")

    if res.status_code != 200:
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")

    return res.json()

def get_all_gdp(year, freq="Q"):
    for table_id in gdp_table_id_map.keys():
        gdp(table_id, year, freq)
