from fastapi import APIRouter

from url_shortener.api.v1.endpoints import url_endpoints


api_router_v1 = APIRouter()

api_router_v1.include_router(url_endpoints.router)