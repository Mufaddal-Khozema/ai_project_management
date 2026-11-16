import socket
import urllib.parse

from piccolo.engine.postgres import PostgresEngine

from config import settings


def _parse_db_url(url: str) -> dict[str, str]:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    config: dict[str, str] = {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
    }
    sslmode = (query.get("sslmode") or [None])[0]
    if sslmode:
        config["ssl"] = sslmode
    return config


def _prefer_ipv4(host: str) -> None:
    """Resolve ``host`` over IPv4 only.

    Managed Postgres providers (e.g. Neon) publish IPv6 addresses that can be
    unreachable from some networks. ``asyncio`` tries resolved addresses
    sequentially, so a black-holed IPv6 address blocks the connect until the
    timeout fires. Restricting resolution to IPv4 avoids that while keeping the
    original hostname for TLS SNI.
    """
    original = socket.getaddrinfo

    def getaddrinfo(h, port, family=0, type=0, proto=0, flags=0):
        if h == host and family in (0, socket.AF_UNSPEC):
            try:
                return original(h, port, socket.AF_INET, type, proto, flags)
            except socket.gaierror:
                return original(h, port, family, type, proto, flags)
        return original(h, port, family, type, proto, flags)

    socket.getaddrinfo = getaddrinfo


DB_CONFIG = _parse_db_url(settings.database_url)
_prefer_ipv4(DB_CONFIG["host"])
DB = PostgresEngine(config=DB_CONFIG)


async def close_db_pool() -> None:
    if DB.pool:
        await DB.close_connection_pool()
