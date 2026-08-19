from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.api.deps import get_db
from url_shortener.services import url_service


router = APIRouter()

@router.get(
    "/{short_code}",
    response_class=RedirectResponse,
)
async def redirect_to_original_url(short_code: str, db: AsyncSession = Depends(get_db)):
    original_url = await url_service.resolve_original_url(db, short_code)
    return RedirectResponse(original_url, status_code=status.HTTP_302_FOUND)
