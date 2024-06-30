"""
Logger with a json formatter.
"""

import json
import logging
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def __init__(self, request_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_id = request_id

    def formatTime(self, record):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat()

    def format(self, record):
        log_record = {
            'level': record.levelname,
            'request_id': getattr(record, 'request_id', self.request_id),
            'message': record.getMessage(),
            'timestamp': self.formatTime(record),
        }

        return json.dumps(log_record)
