from fastapi import APIRouter
from auth import router

auth_router = APIRouter()
auth_router.include_router(router)