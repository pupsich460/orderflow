from fastapi import APIRouter

from routers.v1 import orders_router

main_router = APIRouter()

main_router.include_router(orders_router, prefix="/v1", tags=["orders"])
