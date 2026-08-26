from __future__ import annotations

import os

os.environ.setdefault("LITESTAR_WARN_SYNC_TO_THREAD_WITH_ASYNC", "0")

from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsPlugin
from litestar.plugins.structlog import StructlogPlugin
from litestar_email import EmailConfig, EmailPlugin
from litestar_granian import GranianPlugin

from config import settings
from lib.auth import jwt_auth
from lib.cli import TokenCliPlugin
from lib.tables import create_all_tables
from lib.token_refresh import start_background_tasks
from listeners.email import (
    send_otp_email,
    send_payment_confirmation_email,
    send_renewal_receipt_email,
    send_subscription_cancelled_email,
    send_token_expiry_email,
    send_trial_expiry_email,
)
from listeners.integrations import (
    on_integration_connected,
    on_integration_disconnected,
    on_integration_token_refreshed,
)
from routes import api_router

def create_app() -> Litestar:
    return Litestar(
        route_handlers=[api_router],
        listeners=[
            send_otp_email,
            send_payment_confirmation_email,
            send_renewal_receipt_email,
            send_trial_expiry_email,
            send_subscription_cancelled_email,
            send_token_expiry_email,
            on_integration_connected,
            on_integration_disconnected,
            on_integration_token_refreshed,
        ],
        debug=settings.debug,
        on_app_init=[jwt_auth.on_app_init],
        on_startup=[create_all_tables, start_background_tasks],
        plugins=[
            TokenCliPlugin(),
            GranianPlugin(),
            ProblemDetailsPlugin(
                ProblemDetailsConfig(enable_for_all_http_exceptions=True),
            ),
            StructlogPlugin(),
            EmailPlugin(
                config=EmailConfig(
                    from_email=settings.from_email,
                    from_name=settings.from_name,
                ),
            ),
        ],
        openapi_config=OpenAPIConfig(
            title=settings.app_name,
            version="0.1.0",
            path="/docs",
            root_schema_site="swagger",
        ),
    )


app = create_app()
