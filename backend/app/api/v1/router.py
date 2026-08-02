from fastapi import APIRouter

from app.api.v1.endpoints import catalogue, checkout, health, orders, version
from app.api.v1.endpoints.admin.router import admin_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(version.router, tags=["version"])
api_router.include_router(catalogue.router)
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(admin_router, tags=["admin"])
