import json
import requests

def post_to_channel(webhook_url: str, data_name: str, data):
    msg = {
        "text": f"{data_name}\n```\n{json.dumps(data)}\n```"
    }

    res = requests.post(webhook_url, data=json.dumps(msg), timeout=120)
    if res.status_code != 200:
        raise RuntimeError(f"Unexpected HTTP status code: {res.status_code}")
