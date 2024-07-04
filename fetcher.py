"""
Fetches investments data.
"""

import uuid
import logging
from aws import param_store
from data_source import bea
from data_source import bls
from logger.json_logger import JsonFormatter

# setup logger
json_logger = logging.getLogger()
json_logger.setLevel(logging.INFO)

def _setup_logging(request_id):
    for handler in json_logger.handlers[:]:
        json_logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(request_id))
    json_logger.addHandler(handler)

def _fetch_data(event, context):
    logging.info(f"Event: {event}")
    logging.info(f"Context: {context}")

    logging.info("Fetching finance data...")

    bea_api_key = param_store.get_param_value('/investments-fetcher/bea/api')
    bls_api_key = param_store.get_param_value('/investments-fetcher/bls/api')

    # examples
    if event['data_source'] == "bea":
        logging.info(bea._http_get(bea_api_key, event['data_id'], event['start_year']))
    elif event['data_source'] == "bls":
        logging.info(bls.get_series_data(bls_api_key, event['data_id'], event['start_year'], event['end_year']))

    return "OK"

def lambda_handler(event, context):
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
        "data_source": "bls",
        "data_id": "CUUR0000SA0",
        "start_year": "2023",
        "end_year": "2024",
    }

    _fetch_data(event, None)

if __name__ == "__main__":
    main()
