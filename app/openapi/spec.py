"""
OpenAPI 3.0 specification for the Auth Service.
Served at GET /openapi.json and rendered by Swagger UI at GET /docs.
"""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Auth Service API",
        "version": "1.0.0",
        "description": (
            "Production-ready JWT authentication service built with "
            "Falcon, PostgreSQL, SQLAlchemy, and Kafka."
        ),
        "contact": {"name": "Engineering Team", "email": "eng@example.com"},
    },
    "servers": [{"url": "http://localhost:8000", "description": "Local development"}],
    "tags": [{"name": "Authentication", "description": "User auth endpoints"}],
    "paths": {
        "/register": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Register a new user",
                "operationId": "registerUser",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RegisterRequest"},
                            "example": {
                                "email": "alice@example.com",
                                "password": "Str0ng!Pass",
                                "username": "alice",
                                "phone": "+15550001234",
                            },
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "User registered successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RegisterResponse"}
                            }
                        },
                    },
                    "409": {"description": "Duplicate email / username / phone", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                    "422": {"description": "Validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                },
            }
        },
        "/login": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Authenticate user",
                "operationId": "loginUser",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LoginRequest"},
                            "example": {
                                "email": "alice@example.com",
                                "password": "Str0ng!Pass",
                            },
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Authentication successful",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/LoginResponse"}
                            }
                        },
                    },
                    "401": {"description": "Invalid credentials", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                    "422": {"description": "Validation error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                },
            }
        },
        "/refresh": {
            "post": {
                "tags": ["Authentication"],
                "summary": "Rotate refresh token",
                "operationId": "refreshToken",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RefreshRequest"},
                            "example": {"refresh_token": "<your-refresh-token>"},
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Token rotated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RefreshResponse"}
                            }
                        },
                    },
                    "401": {"description": "Invalid / expired token", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                },
            }
        },
        "/health": {
            "get": {
                "tags": ["System"],
                "summary": "Liveness probe",
                "operationId": "healthCheck",
                "responses": {"200": {"description": "Service is healthy"}},
            }
        },
    },
    "components": {
        "schemas": {
            "RegisterRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email", "example": "alice@example.com"},
                    "password": {"type": "string", "minLength": 8, "example": "Str0ng!Pass"},
                    "username": {"type": "string", "minLength": 3, "example": "alice"},
                    "phone": {"type": "string", "example": "+15550001234"},
                    "org_id": {"type": "string", "format": "uuid", "nullable": True},
                },
            },
            "RegisterResponse": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "format": "uuid"},
                    "email": {"type": "string"},
                    "username": {"type": "string", "nullable": True},
                    "created_at": {"type": "string", "format": "date-time"},
                    "message": {"type": "string"},
                },
            },
            "LoginRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string"},
                },
            },
            "LoginResponse": {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "refresh_token": {"type": "string"},
                    "token_type": {"type": "string", "example": "bearer"},
                    "expires_in": {"type": "integer", "example": 900},
                },
            },
            "RefreshRequest": {
                "type": "object",
                "required": ["refresh_token"],
                "properties": {
                    "refresh_token": {"type": "string"}
                },
            },
            "RefreshResponse": {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "refresh_token": {"type": "string"},
                    "token_type": {"type": "string"},
                    "expires_in": {"type": "integer"},
                },
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        },
    },
    "security": [{"BearerAuth": []}],
}


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Auth Service — API Docs</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.2/swagger-ui.min.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.2/swagger-ui-bundle.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.2/swagger-ui-standalone-preset.min.js"></script>
<script>
  window.onload = function() {
    SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      layout: "StandaloneLayout"
    });
  }
</script>
</body>
</html>
"""
