from fastapi import APIRouter

from .tenant import router

tenant_router = APIRouter()
tenant_router.include_router(router, tags=["租户模块"])

__all__ = ["tenant_router"]