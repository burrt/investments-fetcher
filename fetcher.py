"""
Fetches investments data.
"""

import argparse
import uuid
import logging
import os
import traceback
from datetime import date, datetime, timezone
from aws import param_store
from aws import s3
from data_source import bea
from data_source import bls
from data_source import dol
from data_source import fred
from dotenv import load_dotenv
from logger.json_logger import JsonFormatter
from notifier import slack

DATA_SOURCES = ("bea", "bls", "dol", "fred")
HTTP_TIMEOUT_SECONDS = 120

# setup logger
json_logger = logging.getLogger()
json_logger.setLevel(logging.INFO)

def _setup_logging(request_id: str):
    for handler in json_logger.handlers[:]:
        json_logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(request_id))
    json_logger.addHandler(handler)

def _get_setting(env_name: str, param_name: str, dry_run: bool):
    value = os.getenv(env_name)
    if value:
        return value
    if dry_run:
        raise ValueError(f"--dry-run requires {env_name} in .env or the environment")
    return param_store.get_param_value(param_name)

def _fetch_data(event: dict, context, dry_run: bool = False):
    logging.info(f"Event: {event}")
    logging.info(f"Context: {context}")

    logging.info("Fetching finance data...")

    source = event['data_source']
    if source not in DATA_SOURCES:
        raise ValueError(f"Unsupported data source: {source}")
    api_key = _get_setting(f"{source.upper()}_API_KEY", f"/investments-fetcher/{source}/api", dry_run)
    slack_webhook_url = _get_setting(
        "SLACK_TESTING_WEBHOOK_URL" if dry_run else "SLACK_WEBHOOK_URL",
        '/investments-fetcher/slack/webhook-url',
        dry_run)
    if dry_run:
        logging.info("Dry run: using testing Slack webhook; S3 uploads disabled")

    start_date = event.get('start_year', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    end_date = event.get('end_year', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    freq = event.get('frequency', 'Q')
    data = ""
    data_name = ""
    slack_filtered_data = None

    if event['data_source'] == "bea":
        data, data_name, slack_filtered_data = bea.get_gdp(api_key, event['data_id'], start_date[:4], freq, timeout=HTTP_TIMEOUT_SECONDS)
        end_date = start_date
    elif event['data_source'] == "bls":
        data, data_name, slack_filtered_data = bls.get_series_data(api_key, event['data_id'], start_date[:4], end_date[:4], timeout=HTTP_TIMEOUT_SECONDS)
    elif event['data_source'] == "dol":
        event['data_id'] = "10281"
        data, data_name = dol.get_unemployment_weekly_claims(api_key, timeout=HTTP_TIMEOUT_SECONDS)
    elif event['data_source'] == "fred":
        data, data_name = fred.get_series_data(api_key, event['data_id'], start_date, end_date, freq, timeout=HTTP_TIMEOUT_SECONDS)

    logging.info(data)
    slack.post_to_channel(
        slack_webhook_url,
        event['data_source'],
        event['data_id'],
        data_name,
        slack_filtered_data if slack_filtered_data is not None else data,
        timeout=HTTP_TIMEOUT_SECONDS)

    if not dry_run and os.getenv("SKIP_S3_UPLOAD") == "false":
        s3.upload_data(event['data_source'], event['data_id'], start_date[:4], end_date[:4], data)

    return "OK"

def lambda_handler(event: dict, context):
    """AWS Lambda function entry point for a request.

    Args:
        event (dict): AWS event, json formatted
        context (LambdaContext): AWS request context
    """
    _setup_logging(context.aws_request_id)

    try:
        _fetch_data(event, context)
    except Exception as ex:
        slack_errors_webhook_url = param_store.get_param_value('/investments-fetcher/errors/slack/webhook-url')
        error_json = {
            "type": type(ex).__name__,
            "message": str(ex),
            "traceback": traceback.format_exc()
        }
        slack.post_to_channel(
            slack_errors_webhook_url, event['data_source'], "API ERROR", "Fetch failed",
            error_json, timeout=HTTP_TIMEOUT_SECONDS)

def main():
    """
    Local debugging entry point.
    """
    parser = argparse.ArgumentParser(
        description="Fetch economic data and post it to Slack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # BEA GDP
  python fetcher.py bea T10101 --start 2025-01-01 --end 2025-12-31 --dry-run

  # BLS consumer prices
  python fetcher.py bls CUUR0000SA0 --start 2025-01-01 --end 2025-12-31 --dry-run

  # Latest DOL weekly claims
  python fetcher.py dol --dry-run

BEA uses the start year; BLS uses whole years. DOL always fetches latest data.
Dry runs require the provider's API key and SLACK_TESTING_WEBHOOK_URL in .env.
""")
    parser.add_argument("source", choices=DATA_SOURCES)
    parser.add_argument("data_id", nargs="?", help="BEA table or BLS/FRED series ID; required except for DOL")
    parser.add_argument("--start", type=date.fromisoformat, metavar="YYYY-MM-DD", help="Start date; required except for DOL")
    parser.add_argument("--end", type=date.fromisoformat, metavar="YYYY-MM-DD", help="End date; required except for DOL")
    parser.add_argument("--frequency", help="BEA frequency (default: Q) or FRED frequency (default: m)")
    parser.add_argument("--dry-run", action="store_true", help="Post to testing Slack; skip S3 and Parameter Store")
    args = parser.parse_args()
    if args.source != "dol" and not all((args.data_id, args.start, args.end)):
        parser.error("data_id, --start and --end are required except for DOL")
    if args.start and args.end and args.start > args.end:
        parser.error("--start must be on or before --end")
    _setup_logging(str(uuid.uuid4()))

    load_dotenv(".env")

    today = datetime.now(timezone.utc).date()
    event = {
        "data_source": args.source,
        "data_id": "10281" if args.source == "dol" else args.data_id,
        "start_year": (args.start or today).isoformat(),
        "end_year": (args.end or today).isoformat(),
        "frequency": args.frequency or ("m" if args.source == "fred" else "Q")
    }

    _fetch_data(event, None, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
