import os
from urllib.parse import urlparse

def get_db_config():
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL not set")

    parsed = urlparse(db_url)

    return {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path[1:]  # remove leading "/"
    }
