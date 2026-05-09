"""
FastAPI application factory and entrypoint. Exposes `application` as the
ASGI app for servers and runs via `uvicorn` when executed directly.
"""
from pathlib import Path
import os
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from config import get_settings
from database import SessionLocal
from producer import AuthEventProducer, KafkaProducer
from middleware import JWTAuthMiddleware, RateLimitMiddleware
from auth import router as auth_router 
# from .grpc_server import create_grpc_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)


def create_app() -> FastAPI:
    settings = get_settings()
    kafka_producer = KafkaProducer()
    auth_events = AuthEventProducer(kafka_producer)
    # grpc_server = create_grpc_server(auth_events, settings.auth_grpc_bind_address)

    app = FastAPI()

    # Attach middleware (BaseHTTPMiddleware subclasses are supported)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(JWTAuthMiddleware)


    class _DBSessionMiddleware:
        async def __call__(self, request: Request, call_next):
            request.state.db = SessionLocal()
            try:
                response = await call_next(request)
                return response
            finally:
                db = getattr(request.state, "db", None)
                if db:
                    db.close()


    class _EventsMiddleware:
        def __init__(self, events: AuthEventProducer):
            self._events = events

        async def __call__(self, request: Request, call_next):
            request.state.events = self._events
            return await call_next(request)

    # Mount lightweight callables as Starlette middleware
    app.middleware("http")(_EventsMiddleware(auth_events))
    app.middleware("http")(_DBSessionMiddleware())

    # Include auth router
    app.include_router(auth_router)

    # @app.on_event("startup")
    # def _start_grpc_server() -> None:
    #     grpc_server.start()
    #     logging.getLogger(__name__).info("Auth gRPC server started on %s", settings.auth_grpc_bind_address)

    # @app.on_event("shutdown")
    # def _stop_grpc_server() -> None:
    #     grpc_server.stop(grace=5)
    #     pass

    @app.exception_handler(Exception)
    async def _generic_error_handler(request: Request, exc: Exception):
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            raise exc

        logging.getLogger(__name__).exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please try again later."},
        )

    return app


application = create_app()
app = application


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("AUTH_PORT", "8001"))

    print(f"🚀  Auth service starting at http://{host}:{port}")
    print(f"📖  Swagger UI → http://{host}:{port}/docs")

    uvicorn.run("main:application", host=host, port=port, reload=True)
