import io
import os
import shlex
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

import fetcher


class FetcherTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "BEA_API_KEY": "local-key",
            "SLACK_TESTING_WEBHOOK_URL": "https://testing.example/webhook",
            "SLACK_WEBHOOK_URL": "https://production.example/webhook",
            "SKIP_S3_UPLOAD": "false",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        timeout = patch("fetcher.HTTP_TIMEOUT_SECONDS", 17)
        timeout.start()
        self.addCleanup(timeout.stop)
        for name in ("param_store.get_param_value", "s3.upload_data", "slack.post_to_channel"):
            patcher = patch(f"fetcher.{name}")
            setattr(self, name.split(".")[-1], patcher.start())
            self.addCleanup(patcher.stop)
        self.event = {
            "data_source": "bea", "data_id": "T10101",
            "start_year": "2025", "end_year": "2026", "frequency": "Q",
        }

    def test_dry_run_uses_testing_slack_and_never_aws_for_each_provider(self):
        self.get_param_value.side_effect = AssertionError("Unexpected AWS lookup")
        self.upload_data.side_effect = AssertionError("Unexpected S3 upload")
        providers = (
            ("bea", "get_gdp", ({"raw": True}, "GDP", {"latest": True})),
            ("bls", "get_series_data", ({"raw": True}, "CPI", {"latest": True})),
            ("dol", "get_unemployment_weekly_claims", ({"raw": True}, "Claims")),
            ("fred", "get_series_data", ({"raw": True}, "Sentiment")),
        )
        for source, method, result in providers:
            with self.subTest(source=source):
                self.event["data_source"] = source
                # Only the selected provider's key is available.
                with patch.dict(os.environ, {
                    f"{source.upper()}_API_KEY": "local-key",
                    "SLACK_TESTING_WEBHOOK_URL": "https://testing.example/webhook",
                    "SLACK_WEBHOOK_URL": "https://production.example/webhook",
                    "SKIP_S3_UPLOAD": "false",
                }, clear=True), patch(f"fetcher.{source}.{method}", return_value=result) as provider:
                    self.assertEqual(fetcher._fetch_data(self.event, None, dry_run=True), "OK")
                    self.assertEqual(provider.call_args.args[0], "local-key")
                    self.assertEqual(provider.call_args.kwargs["timeout"], 17)
                    self.assertEqual(self.post_to_channel.call_args.args[0], "https://testing.example/webhook")
                    self.assertEqual(self.post_to_channel.call_args.kwargs["timeout"], 17)
                    self.assertEqual(self.post_to_channel.call_args.args[-1], result[2] if len(result) == 3 else result[0])
        self.get_param_value.assert_not_called()
        self.upload_data.assert_not_called()

    def test_missing_dry_run_settings_fail_without_production_fallback(self):
        for missing in ("BEA_API_KEY", "SLACK_TESTING_WEBHOOK_URL"):
            with self.subTest(missing=missing), patch.dict(os.environ):
                del os.environ[missing]
                with patch("fetcher.bea.get_gdp") as provider:
                    with self.assertRaisesRegex(ValueError, missing):
                        fetcher._fetch_data(self.event, None, dry_run=True)
                    provider.assert_not_called()
        self.get_param_value.assert_not_called()
        self.upload_data.assert_not_called()
        self.post_to_channel.assert_not_called()

    @patch("fetcher.bea.get_gdp", return_value=({"raw": True}, "GDP", {"latest": True}))
    def test_normal_run_uses_production_slack_and_configured_s3(self, provider):
        fetcher._fetch_data(self.event, None)
        self.assertEqual(self.post_to_channel.call_args.args[0], "https://production.example/webhook")
        self.upload_data.assert_called_once()
        self.get_param_value.assert_not_called()

    @patch("fetcher.bea.get_gdp", return_value=({}, "GDP", {}))
    def test_normal_run_retains_parameter_store_fallback(self, provider):
        del os.environ["BEA_API_KEY"]
        del os.environ["SLACK_WEBHOOK_URL"]
        self.get_param_value.side_effect = ["aws-key", "aws-webhook"]
        fetcher._fetch_data(self.event, None)
        self.assertEqual(provider.call_args.args[0], "aws-key")
        self.assertEqual(self.post_to_channel.call_args.args[0], "aws-webhook")

    @patch("fetcher.bea.get_gdp", return_value=({}, "GDP", {}))
    def test_normal_run_respects_skip_s3(self, provider):
        os.environ["SKIP_S3_UPLOAD"] = "true"
        fetcher._fetch_data(self.event, None)
        self.upload_data.assert_not_called()

    @patch("fetcher.load_dotenv")
    @patch("fetcher._setup_logging")
    @patch("fetcher._fetch_data")
    def test_help_examples_build_events(self, fetch, setup_logging, load_dotenv):
        output = io.StringIO()
        with patch("sys.argv", ["fetcher.py", "--help"]), redirect_stdout(output):
            with self.assertRaises(SystemExit) as exit:
                fetcher.main()
        self.assertEqual(exit.exception.code, 0)
        fetch.assert_not_called()
        examples = [line.strip() for line in output.getvalue().splitlines()
                    if line.strip().startswith("python fetcher.py ")]
        self.assertEqual(len(examples), 3)
        for command in examples:
            with self.subTest(command=command), patch("sys.argv", shlex.split(command)[1:]):
                fetcher.main()
                event = fetch.call_args.args[0]
                self.assertEqual(fetch.call_args.kwargs, {"dry_run": True})
                if event["data_source"] == "dol":
                    self.assertEqual(event["data_id"], "10281")
                else:
                    self.assertEqual(event["data_id"], "T10101" if event["data_source"] == "bea" else "CUUR0000SA0")
                    self.assertEqual(event["start_year"], "2025-01-01")
                    self.assertEqual(event["end_year"], "2025-12-31")

    @patch("fetcher._fetch_data")
    def test_invalid_cli_inputs_fail_before_fetching(self, fetch):
        cases = (
            [],
            ["bea", "T10101"],
            ["bea", "--start", "2025-01-01", "--end", "2025-12-31"],
            ["bls", "CUUR0000SA0", "--start", "invalid", "--end", "2025-12-31"],
            ["bls", "CUUR0000SA0", "--start", "2025-12-31", "--end", "2025-01-01"],
        )
        for args in cases:
            with self.subTest(args=args), patch("sys.argv", ["fetcher.py", *args]), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exit:
                    fetcher.main()
                self.assertEqual(exit.exception.code, 2)
        fetch.assert_not_called()

    @patch("fetcher.load_dotenv")
    @patch("fetcher._setup_logging")
    @patch("fetcher._fetch_data")
    def test_fred_cli_passes_dates_and_frequency(self, fetch, setup_logging, load_dotenv):
        argv = ["fetcher.py", "fred", "UMCSENT", "--start", "2025-01-01", "--end", "2025-12-31"]
        with patch("sys.argv", argv):
            fetcher.main()
        self.assertEqual(fetch.call_args.args[0], {
            "data_source": "fred", "data_id": "UMCSENT", "start_year": "2025-01-01",
            "end_year": "2025-12-31", "frequency": "m",
        })
        self.assertEqual(fetch.call_args.kwargs, {"dry_run": False})


class HttpTimeoutTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("fetcher.bea.filter_data_to_latest_datapoint", return_value={})
    @patch("fetcher.bls.filter_data_to_latest_datapoint", return_value={})
    def test_modules_forward_timeout_to_http_requests(self, bls_filter, bea_filter):
        cases = (
            (fetcher.bea.get_gdp, ("key", "T10101", "2025"), "get"),
            (fetcher.bls.get_series_data, ("key", "CUUR0000SA0", "2025", "2026"), "post"),
            (fetcher.dol.get_unemployment_weekly_claims, ("key",), "get"),
            (fetcher.fred.get_series_data, ("key", "UMCSENT", "2025-01-01", "2026-01-01", "m"), "get"),
            (fetcher.slack.post_to_channel, ("https://testing.example/webhook", "bea", "T10101", "GDP", {}), "post"),
        )
        for function, args, method in cases:
            with self.subTest(module=function.__module__), patch(f"requests.{method}") as request:
                request.return_value.status_code = 200
                request.return_value.json.return_value = {}
                function(*args, timeout=17)
                self.assertEqual(request.call_args.kwargs["timeout"], 17)
                if function is fetcher.fred.get_series_data:
                    self.assertEqual(request.call_args.kwargs["params"]["observation_end"], "2026-01-01")
