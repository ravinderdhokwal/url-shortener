from fastapi import APIRouter

from url_shortener.api import url_apis


api_router_v1 = APIRouter()

api_router_v1.include_router(url_apis.router)