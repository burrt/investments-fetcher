"""
Module for the AWS SDK.
"""

import boto3

def get_param_value(param_key: str) -> str:
    """Gets the parameter value for given parameter key from AWS SSM Parameter Store

    Args:
        param_key (str): parameter key

    Returns:
        str: parameter value
    """
    ssm = boto3.client('ssm')
    return ssm.get_parameter(Name=param_key, WithDecryption=True)['Parameter']['Value']
