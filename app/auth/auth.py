"""
FastAPI router for authentication endpoints.

Replaces the previous Falcon resource classes with an `APIRouter` that
exposes the same endpoints and reuses existing Pydantic schemas and
service layer.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from producer import AuthEventProducer
from schema import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    CreateOrgRequest,
    CreateOrgResponse,
)
from service import (
    AuthenticationError,
    AuthService,
    RegistrationError,
    TokenError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_service(request: Request) -> AuthService:
    db: Session = request.state.db
    events: AuthEventProducer = request.state.events
    return AuthService(db=db, events=events)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request) -> RegisterResponse:
    svc = _get_service(request)

    try:
        result = svc.register(
            email=payload.email,
            password=payload.password,
            username=payload.username,
            phone=payload.phone,
            org_id=payload.org_id,
        )
        return result
    except RegistrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during registration")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    svc = _get_service(request)

    try:
        result = svc.login(email=payload.email, password=payload.password)
        return result
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during login")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, request: Request) -> RefreshResponse:
    svc = _get_service(request)

    try:
        result = svc.refresh(raw_refresh_token=payload.refresh_token)
        return result
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during token refresh")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc

@router.post("/org", response_model=CreateOrgResponse, status_code=status.HTTP_201_CREATED)
def create_org(payload: CreateOrgRequest, request: Request) -> CreateOrgResponse:
    svc = _get_service(request)

    try:
        result = svc.create_org(
            name=payload.name,
            slug=payload.slug,
            admin_email=payload.admin_email,
            admin_password=payload.admin_password,
            admin_username=payload.admin_username,
            admin_phone=payload.admin_phone,
        )
        return CreateOrgResponse(
            org_id=str(result.id),
            name=result.name,
            slug=result.slug,
            owner_user_id=str(result.owner_user_id),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during organization creation")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc
    

@router.get("/org/{org_id}", response_model=CreateOrgResponse)
def get_org(org_id: str, request: Request) -> CreateOrgResponse:
    svc = _get_service(request)

    try:
        result = svc.get_org(org_id=org_id)
        return CreateOrgResponse(
            org_id=str(result.id),
            name=result.name,
            slug=result.slug,
            owner_user_id=str(result.owner_user_id),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during organization retrieval")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc
    
@router.post("/org/{org_id}/invite", status_code=status.HTTP_200_OK)
def invite_member(org_id: str, user_id: str, request: Request) -> dict:
    svc = _get_service(request)

    try:
        svc.invite_member(org_id=org_id, user_id=user_id)
        return {"message": "User invited successfully."}
    
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during member invitation")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc
    

@router.delete("/org/{org_id}/member/{user_id}", status_code=status.HTTP_200_OK)
def remove_member(org_id: str, user_id: str, request: Request) -> dict:
    svc = _get_service(request)

    try:
        svc.remove_member(org_id=org_id, user_id=user_id)
        return {"message": "User removed successfully."}
    
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during member removal")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.") from exc
    


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
