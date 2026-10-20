from datetime import datetime, timezone
from uuid import uuid4


def utc():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid4())
