import urllib.parse

from piccolo.engine.postgres import PostgresEngine

from config import settings


def _parse_db_url(url: str) -> dict[str, str]:
    parsed = urllib.parse.urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
    }


DB = PostgresEngine(config=_parse_db_url(settings.database_url))
