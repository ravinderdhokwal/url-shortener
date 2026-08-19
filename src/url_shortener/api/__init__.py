from url_shortener.api.router import api_router_v1
from url_shortener.api.url_redirect import router as redirect_router

api_router = api_router_v1

redirect_router = redirect_router

__all__ = ["api_router", "redirect_router"]