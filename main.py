"""
Entry point — starts the Gunicorn WSGI server programmatically.

Run directly:
    python main.py

Or via Gunicorn CLI:
    gunicorn main:application --bind 0.0.0.0:8000 --workers 4
"""
import os

# from app import create_app

# # WSGI callable expected by Gunicorn
# application = create_app()

"""
Falcon application factory.

Usage::

    from app import create_app
    application = create_app()
"""
import logging

import falcon

from app.core.database import SessionLocal
from kafka_app.producer import AuthEventProducer, KafkaProducer
from app.auth.middleware import JWTAuthMiddleware, RateLimitMiddleware
from app.auth.auth import (
    HealthResource,
    LoginResource,
    RefreshResource,
    RegisterResource,
)
from app.openapi.docs_resource import OpenAPISpecResource, SwaggerUIResource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)


def create_app() -> falcon.App:
    """Construct and return the configured Falcon WSGI application."""

    kafka_producer = KafkaProducer()
    auth_events = AuthEventProducer(kafka_producer)

    app = falcon.App(
        middleware=[
            RateLimitMiddleware(),
            _DBSessionMiddleware(),
            _EventsMiddleware(auth_events),
            JWTAuthMiddleware(),
        ]
    )

    app.add_route("/health", HealthResource())
    app.add_route("/register", RegisterResource())
    app.add_route("/login", LoginResource())
    app.add_route("/refresh", RefreshResource())
    app.add_route("/openapi.json", OpenAPISpecResource())
    app.add_route("/docs", SwaggerUIResource())

    app.add_error_handler(Exception, _generic_error_handler)

    return app


class _DBSessionMiddleware:
    """Open a DB session per request and guarantee its cleanup."""

    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        req.context.db = SessionLocal()

    def process_response(
        self,
        req: falcon.Request,
        resp: falcon.Response,
        resource,
        req_succeeded: bool,
    ) -> None:
        db = getattr(req.context, "db", None)
        if db:
            db.close()


class _EventsMiddleware:
    """Attach the Kafka event producer to every request context."""

    def __init__(self, events: AuthEventProducer) -> None:
        self._events = events

    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        req.context.events = self._events


def _generic_error_handler(
    req: falcon.Request,
    resp: falcon.Response,
    ex: Exception,
    params: dict,
) -> None:
    """Convert unhandled exceptions to JSON 500 responses."""
    if isinstance(ex, falcon.HTTPError):
        raise ex

    logging.getLogger(__name__).exception("Unhandled exception")
    raise falcon.HTTPInternalServerError(
        title="Internal Server Error",
        description="An unexpected error occurred. Please try again later.",
    )

application = create_app()

if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))

    print(f"🚀  Auth service starting at http://{host}:{port}")
    print(f"📖  Swagger UI → http://{host}:{port}/docs")

    with make_server(host, port, application) as httpd:
        httpd.serve_forever()
