"""
Module for AWS S3.
"""

import json
from datetime import datetime, timezone
import boto3

def upload_data(data_source: str, data_id: str, start_year: int, end_year: int, data):
    """Upload the data to S3 as a json file.
    The file name will be suffixed with the current UTC date.

    Args:
        data_source (str): data source name
        data_id (str): data ID
        start_year (int): start year of the data
        end_year (int): end year of the data
        data: json encoded blob to upload to S3
    """
    curr_utc_datetime = datetime.now(timezone.utc)
    curr_utc_date = curr_utc_datetime.strftime('%Y-%m-%d')
    s3_file_name = f"{data_source}_{data_id}-{start_year}-{end_year}_{curr_utc_date}.json"

    s3 = boto3.client('s3')
    s3.put_object(Bucket="investments-fetcher.latest", Key=s3_file_name, Body=json.dumps(data))
