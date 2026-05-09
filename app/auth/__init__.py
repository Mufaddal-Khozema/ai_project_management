from fastapi import APIRouter
from app.auth.auth import router

auth_router = APIRouter()
auth_router.include_router(router)