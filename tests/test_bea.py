"""Offline BEA adapter tests using a dated, credential-free API snapshot.

Summary tests exercise real observations; request tests mock only HTTP. Each
fixture load returns fresh data so tests can edit rows without affecting others.
"""

import copy
import json
import os
import traceback
import unittest
from pathlib import Path
from unittest.mock import call, patch

import requests

from data_source import bea


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bea_nipa_gdp.json"


def load_payload(table_id="T10101"):
    """Load an independent copy of one table's recorded API response."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return fixture["tables"][table_id]


def gdp_row(payload, period="2026Q3"):
    """Find the fixture's GDP row by period, without relying on row order."""
    rows = payload["BEAAPI"]["Results"]["Data"]
    return next(
        row for row in rows
        if row["LineNumber"] == "1" and row["TimePeriod"] == period
    )


class BeaSummaryTests(unittest.TestCase):
    def test_headline_matches_dated_release_without_reannualization(self):
        # BEA's 2026-10-29 advance release: Q3 real GDP +3.4% SAAR.
        payload = load_payload()

        summary = bea.filter_data_to_latest_datapoint(payload, "T10101")

        self.assertIsInstance(summary, dict)  # Regression: previously a nested tuple.
        self.assertEqual(summary["period"], "2026Q3")
        self.assertEqual(summary["value"], "3.4")
        self.assertEqual(summary["calculation"], "Percent change, annual rate")
        self.assertEqual(
            summary["basis"],
            "Change from preceding quarter, seasonally adjusted annual rate",
        )
        self.assertNotIn("percentage_change", summary)

    def test_all_eight_gdp_rows_preserve_distinct_measures_and_scales(self):
        # Values and source metadata pinned from live API responses, 2026-11-06.
        expected = {
            "T10101": ("A191RL", "3.4", "Fisher Quantity Index", 0),
            "T10102": ("A191RL", "3.4", "Fisher Quantity Index", 0),
            "T10103": ("A191RA", "125.489", "Fisher Quantity Index", 0),
            "T10104": ("A191RG", "134.168", "Fisher Price Index", 0),
            "T10105": ("A191RC", "33,010,036", "Current Dollars", 6),
            "T10106": ("A191RX", "24,611,077", "Chained Dollars", 6),
            "T10107": ("A191RV", "2.3", "Fisher Price Index", 0),
            "T10108": ("A191RV", "2.3", "Fisher Price Index", 0),
        }
        for table_id, (series_code, value, metric, multiplier) in expected.items():
            with self.subTest(table_id=table_id):
                payload = load_payload(table_id)

                summary = bea.filter_data_to_latest_datapoint(payload, table_id)

                self.assertEqual(summary["series_code"], series_code)
                self.assertEqual(summary["value"], value)
                self.assertEqual(summary["metric"], metric)
                self.assertEqual(summary["unit_multiplier"], multiplier)
                self.assertEqual(summary["period"], "2026Q3")
                self.assertEqual(
                    [note["NoteRef"] for note in summary["source_notes"]],
                    [table_id],
                )
                self.assertNotIn("percentage_change", summary)

    def test_summary_does_not_modify_source_payload(self):
        payload = load_payload()
        original = copy.deepcopy(payload)

        bea.filter_data_to_latest_datapoint(payload, "T10101")

        self.assertEqual(payload, original)

    def test_dollar_scale_comes_from_row_not_billions_in_table_note(self):
        payload = load_payload("T10105")

        summary = bea.filter_data_to_latest_datapoint(payload, "T10105")

        self.assertIn("Billions of dollars", summary["source_notes"][0]["NoteText"])
        self.assertEqual(summary["unit_multiplier"], 6)
        self.assertEqual(summary["calculation"], "Level")
        self.assertEqual(summary["basis"], "Level, seasonally adjusted annual rate")

    def test_index_preserves_reference_year_without_becoming_growth(self):
        payload = load_payload("T10104")

        summary = bea.filter_data_to_latest_datapoint(payload, "T10104")

        self.assertEqual(summary["calculation"], "Level")
        self.assertEqual(summary["basis"], "Seasonally adjusted index")
        self.assertIn("2017=100", summary["source_notes"][0]["NoteText"])

    def test_latest_quarter_is_selected_regardless_of_response_order(self):
        for periods in (("2026Q2", "2026Q3"), ("2026Q3", "2026Q2")):
            with self.subTest(periods=periods):
                payload = load_payload()
                payload["BEAAPI"]["Results"]["Data"] = [
                    gdp_row(payload, period) for period in periods
                ]

                summary = bea.filter_data_to_latest_datapoint(payload, "T10101")

                self.assertEqual(summary["period"], "2026Q3")

    def test_gdp_selection_does_not_depend_on_description(self):
        payload = load_payload()
        gdp_row(payload)["LineDescription"] = "Description changed by publisher"

        summary = bea.filter_data_to_latest_datapoint(payload, "T10101")

        self.assertEqual(summary["period"], "2026Q3")
        self.assertEqual(summary["value"], "3.4")

    def test_rows_with_a_different_table_series_or_line_are_ignored(self):
        mismatches = {
            "TableName": "T10102",
            "SeriesCode": "DPCERL",
            "LineNumber": "2",
        }
        for field, value in mismatches.items():
            with self.subTest(field=field):
                payload = load_payload()
                unrelated_row = dict(gdp_row(payload))
                unrelated_row.update(TimePeriod="2027Q4", DataValue="999")
                unrelated_row[field] = value
                payload["BEAAPI"]["Results"]["Data"].append(unrelated_row)

                summary = bea.filter_data_to_latest_datapoint(payload, "T10101")

                self.assertEqual(summary["period"], "2026Q3")
                self.assertEqual(summary["value"], "3.4")

    def test_quarterly_summary_ignores_a_more_recent_annual_observation(self):
        payload = load_payload()
        annual_row = dict(gdp_row(payload, "2025"))
        annual_row.update(TimePeriod="2027", DataValue="999")
        payload["BEAAPI"]["Results"]["Data"].append(annual_row)

        summary = bea.filter_data_to_latest_datapoint(payload, "T10101", "Q")

        self.assertEqual(summary["period"], "2026Q3")

    def test_annual_summary_ignores_quarterly_observations(self):
        payload = load_payload()

        summary = bea.filter_data_to_latest_datapoint(payload, "T10101", "A")

        self.assertEqual(summary["period"], "2025")
        self.assertEqual(summary["value"], "2.3")
        self.assertEqual(summary["frequency"], "A")
        self.assertEqual(summary["basis"], "Change from previous calendar year")

    def test_unavailable_latest_value_does_not_fall_back_to_older_gdp(self):
        for unavailable in ("(NA)", "...", "NaN", "Infinity", "", None):
            with self.subTest(value=unavailable):
                payload = load_payload()
                gdp_row(payload)["DataValue"] = unavailable

                with self.assertRaisesRegex(RuntimeError, "value or units are unavailable"):
                    bea.filter_data_to_latest_datapoint(payload, "T10101")

    def test_missing_gdp_fails_clearly(self):
        payload = {"BEAAPI": {"Results": {"Data": []}}}

        with self.assertRaisesRegex(RuntimeError, "no GDP observations"):
            bea.filter_data_to_latest_datapoint(payload, "T10101")

    def test_missing_scale_fails_instead_of_guessing(self):
        payload = load_payload("T10105")
        del gdp_row(payload)["UNIT_MULT"]

        with self.assertRaisesRegex(RuntimeError, "value or units are unavailable"):
            bea.filter_data_to_latest_datapoint(payload, "T10105")

    def test_duplicate_latest_gdp_fails(self):
        payload = load_payload()
        duplicate = copy.deepcopy(gdp_row(payload))
        rows = payload["BEAAPI"]["Results"]["Data"]
        rows.append(duplicate)

        with self.assertRaisesRegex(RuntimeError, "duplicate latest"):
            bea.filter_data_to_latest_datapoint(payload, "T10101")

    def test_invalid_quarter_fails(self):
        payload = load_payload()
        gdp_row(payload)["TimePeriod"] = "2026Q5"

        with self.assertRaisesRegex(RuntimeError, "invalid GDP period"):
            bea.filter_data_to_latest_datapoint(payload, "T10101")


class BeaRequestTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"SKIP_LOCAL_DEBUG_PAYLOAD": "true"}))
        self.http_get = self.enterContext(
            patch("data_source.bea.requests.get", autospec=True)
        )
        self.response = self.http_get.return_value
        self.response.status_code = 200
        self.response.json.return_value = load_payload()

    def test_request_uses_nipa_parameters_and_explicit_timeout(self):
        bea.get_gdp("test-api-key", "T10101", "2026", timeout=17)

        self.http_get.assert_called_once_with(
            "https://apps.bea.gov/api/data",
            params={
                "UserID": "test-api-key",
                "method": "GetData",
                "DataSetName": "NIPA",
                "Year": "2026",
                "TableName": "T10101",
                "Frequency": "Q",
                "ResultFormat": "JSON",
            },
            timeout=17,
        )

    def test_returns_payload_label_and_summary(self):
        data, label, summary = bea.get_gdp("test-api-key", "T10101", "2026", timeout=17)

        self.assertEqual(data, load_payload())
        self.assertEqual(
            label,
            "NIPA Table 1.1.1. Percent Change From Preceding Period "
            "in Real Gross Domestic Product",
        )
        self.assertEqual(summary["value"], "3.4")

    def test_echoed_credential_is_redacted_without_changing_other_data(self):
        payload = self.response.json.return_value
        payload["BEAAPI"]["Request"] = {
            "RequestParam": [
                {"ParameterName": "USERID", "ParameterValue": "test-api-key"},
                {"ParameterName": "TABLENAME", "ParameterValue": "T10101"},
            ]
        }
        expected_payload = copy.deepcopy(payload)
        expected_payload["BEAAPI"]["Request"]["RequestParam"][0]["ParameterValue"] = "[REDACTED]"

        data, _, _ = bea.get_gdp("test-api-key", "T10101", "2026", timeout=17)

        self.assertEqual(data, expected_payload)

    def test_lowercase_frequency_is_normalized_in_request_and_summary(self):
        for frequency in ("a", "q"):
            with self.subTest(frequency=frequency):
                _, _, summary = bea.get_gdp(
                    "test-api-key", "T10101", "2026", frequency, timeout=17,
                )

                params = self.http_get.call_args.kwargs["params"]
                self.assertEqual(params["Frequency"], frequency.upper())
                self.assertEqual(summary["frequency"], frequency.upper())

    def test_unsupported_table_or_frequency_fails_before_http(self):
        for table_id, frequency in (("unknown", "Q"), ("T10101", "M"), ("T10101", "A,Q")):
            with self.subTest(table_id=table_id, frequency=frequency):
                with self.assertRaises(ValueError):
                    bea.get_gdp("test-api-key", table_id, "2026", frequency, timeout=17)

                self.http_get.assert_not_called()

    def test_http_200_error_envelopes_fail(self):
        error_envelopes = {
            "results_error": {"Results": {"Error": {"APIErrorCode": "1"}}},
            "top_level_error": {"Error": {"APIErrorCode": "1"}},
        }
        for name, envelope in error_envelopes.items():
            with self.subTest(envelope=name):
                self.response.json.return_value = {"BEAAPI": envelope}

                with self.assertRaisesRegex(RuntimeError, "BEA API returned an error"):
                    bea.get_gdp("test-api-key", "T10101", "2026", timeout=17)

    def test_http_failure_does_not_require_json_body(self):
        self.response.status_code = 503

        with self.assertRaisesRegex(RuntimeError, "HTTP status code: 503"):
            bea.get_gdp("test-api-key", "T10101", "2026", timeout=17)

        self.response.json.assert_not_called()

    def test_invalid_json_fails_clearly(self):
        self.response.json.side_effect = ValueError("Not JSON")

        with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            bea.get_gdp("test-api-key", "T10101", "2026", timeout=17)

    def test_transport_error_does_not_expose_credential_in_traceback(self):
        api_key = "test-api-key"
        self.http_get.side_effect = requests.Timeout(
            f"https://apps.bea.gov/api/data?UserID={api_key}"
        )

        # Capture inside the handler: assertRaises removes the traceback.
        try:
            bea.get_gdp(api_key, "T10101", "2026", timeout=17)
        except RuntimeError:
            failure_traceback = traceback.format_exc()
        else:
            self.fail("Expected RuntimeError")

        self.assertNotIn(api_key, failure_traceback)


class BeaBulkFetchTests(unittest.TestCase):
    @patch("data_source.bea.get_gdp", autospec=True)
    def test_bulk_fetch_maps_each_result_to_its_table(self, get_gdp):
        table_ids = (
            "T10101", "T10102", "T10103", "T10104",
            "T10105", "T10106", "T10107", "T10108",
        )
        expected_results = {
            table_id: ({"table": table_id}, f"Label for {table_id}", {"value": str(index)})
            for index, table_id in enumerate(table_ids)
        }

        def result_for_table(api_key, table_id, year, freq, *, timeout):
            return expected_results[table_id]

        get_gdp.side_effect = result_for_table

        result = bea.get_all_gdp("test-api-key", "2026", "A", timeout=17)

        self.assertEqual(result, expected_results)
        self.assertCountEqual(
            get_gdp.call_args_list,
            [call("test-api-key", table_id, "2026", "A", timeout=17) for table_id in table_ids],
        )
