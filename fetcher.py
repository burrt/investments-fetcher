import uuid
import logging
from aws import param_store
from data_source import bea
from data_source import bls
from logger.json_logger import JsonFormatter

# setup logger
json_logger = logging.getLogger()
json_logger.setLevel(logging.INFO)

def setup_logging(request_id):
    for handler in json_logger.handlers[:]:
        json_logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(request_id))
    json_logger.addHandler(handler)

def fetch_data(event, context):
    logging.info(f"Event: {event}")
    logging.info(f"Context: {context}")

    logging.info("Fetching finance data...")

    bea_api_key = param_store.get_param_value('/investments-fetcher/bea/api')
    bls_api_key = param_store.get_param_value('/investments-fetcher/bls/api')

    # examples
    if event['data_source'] == "bea":
        logging.info(bea.gdp(bea_api_key, event['data_id'], event['start_year']))
    elif event['data_source'] == "bls":
        logging.info(bls.get_series_data(bls_api_key, event['data_id'], event['start_year'], event['end_year']))

    return "OK"

def lambda_handler(event, context):
    setup_logging(context.request_id)
    fetch_data(event, context)

def main():
    setup_logging(str(uuid.uuid4()))
    event = {
        "data_source": "bls",
        "data_id": "CUUR0000SA0",
        "start_year": "2023",
        "end_year": "2024",
    }

    fetch_data(event, None)

if __name__ == "__main__":
    main()
