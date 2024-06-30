import boto3

def get_param_value(param_name):
    ssm = boto3.client('ssm')
    return ssm.get_parameter(Name=param_name, WithDecryption=True)['Parameter']['Value']
