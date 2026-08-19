import uvicorn
from url_shortener.core.config import settings

def main():
    uvicorn.run(
        "url_shortener.app:app",
        host="0.0.0.0", 
        port=settings.PORT,
        reload=settings.IS_DEV_ENV
    )