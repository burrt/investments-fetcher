"""
Fetches investments data.
"""

import uuid
import logging
from aws import param_store
from aws import s3
from data_source import bea
from data_source import bls
from data_source import dol
from logger.json_logger import JsonFormatter
from notifier import slack

# setup logger
json_logger = logging.getLogger()
json_logger.setLevel(logging.INFO)

def _setup_logging(request_id: str):
    for handler in json_logger.handlers[:]:
        json_logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(request_id))
    json_logger.addHandler(handler)

def _fetch_data(event: dict, context):
    logging.info(f"Event: {event}")
    logging.info(f"Context: {context}")

    logging.info("Fetching finance data...")

    bea_api_key = param_store.get_param_value('/investments-fetcher/bea/api')
    bls_api_key = param_store.get_param_value('/investments-fetcher/bls/api')
    dol_api_key = param_store.get_param_value('/investments-fetcher/dol/api')
    slack_webhook_url = param_store.get_param_value('/investments-fetcher/slack/webhook-url')

    start_year = event['start_year']
    end_year = event['end_year']
    freq = event.get('frequency', 'Q')
    data = ""
    data_name = ""

    if event['data_source'] == "bea":
        data, data_name = bea.get_gdp(bea_api_key, event['data_id'], start_year, freq)
        end_year = start_year
    elif event['data_source'] == "bls":
        data, data_name = bls.get_series_data(bls_api_key, event['data_id'], start_year, end_year)
    elif event['data_source'] == "dol":
        event['data_id'] = "10281"
        data, data_name = dol.get_unemployment_weekly_claims(dol_api_key)

    logging.info(data)
    slack.post_to_channel(slack_webhook_url, data_name, data)

    s3.upload_data(event['data_source'], event['data_id'], start_year, end_year, data)

    return "OK"

def lambda_handler(event: dict, context):
    """AWS Lambda function entry point for a request.

    Args:
        event (dict): AWS event, json formatted
        context (LambdaContext): AWS request context
    """
    _setup_logging(context.aws_request_id)
    _fetch_data(event, context)

def main():
    """
    Local debugging entry point.
    """
    _setup_logging(str(uuid.uuid4()))
    event = {
        "data_source": "bea",
        "data_id": "T10101",
        "start_year": "2025",
        "end_year": "2025",
        "frequency": "Q"
    }

    _fetch_data(event, None)

if __name__ == "__main__":
    main()
