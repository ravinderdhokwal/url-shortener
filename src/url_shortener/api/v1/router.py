from fastapi import APIRouter

from url_shortener.api.v1.endpoints import urls


api_router_v1 = APIRouter()

api_router_v1.include_router(urls.router)