"""Internal gRPC service used by the organization service to provision admins."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import uuid

import grpc

from app.auth.service import AuthService, RegistrationError
from app.core.database import SessionLocal
from app.core.grpc import (
    CreateAdminUserRequest,
    CreateAdminUserResponse,
    register_auth_provisioning_service,
)
from kafka_app.producer import AuthEventProducer

logger = logging.getLogger(__name__)


class AuthProvisioningGrpcService:
    def __init__(self, events: AuthEventProducer) -> None:
        self._events = events

    def CreateAdminUser(
        self,
        request: CreateAdminUserRequest,
        context: grpc.ServicerContext,
    ) -> CreateAdminUserResponse:
        db = SessionLocal()
        try:
            service = AuthService(db=db, events=self._events)
            result = service.register(
                email=request.email,
                password=request.password,
                username=request.username,
                phone=request.phone,
                org_id=uuid.UUID(request.org_id) if request.org_id else None,
                role_name=request.role_name,
            )
            return CreateAdminUserResponse(
                user_id=str(result.user_id),
                email=result.email,
                org_id=request.org_id,
            )
        except RegistrationError as exc:
            db.rollback()
            context.abort(grpc.StatusCode.ALREADY_EXISTS, str(exc))
        except Exception:
            db.rollback()
            logger.exception("Unexpected error during admin provisioning")
            context.abort(grpc.StatusCode.INTERNAL, "Failed to create admin user.")
        finally:
            db.close()


def create_grpc_server(events: AuthEventProducer, bind_address: str) -> grpc.Server:
    server = grpc.server(ThreadPoolExecutor(max_workers=4))
    register_auth_provisioning_service(server, AuthProvisioningGrpcService(events=events))
    server.add_insecure_port(bind_address)
    return server