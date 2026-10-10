from datetime import datetime, timezone

from litestar import Router, get

@get("/health", operation_id="healthCheck")
async def health_check() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

router = Router(path="", route_handlers=[health_check], tags=["health"])
