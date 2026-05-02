"""
Falcon resources to serve the OpenAPI spec and Swagger UI.
"""
import json

import falcon

from app.openapi.spec import OPENAPI_SPEC, SWAGGER_UI_HTML


class OpenAPISpecResource:
    """GET /openapi.json — Serve the raw OpenAPI 3 JSON spec."""

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        resp.content_type = "application/json"
        resp.text = json.dumps(OPENAPI_SPEC, indent=2)


class SwaggerUIResource:
    """GET /docs — Render Swagger UI."""

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        resp.content_type = "text/html"
        resp.text = SWAGGER_UI_HTML
