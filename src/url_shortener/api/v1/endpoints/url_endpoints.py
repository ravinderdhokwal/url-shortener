from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.api.deps import get_db
from url_shortener.schemas.url_schema import URLCreate, URLResponse
from url_shortener.services import url_service


router = APIRouter(prefix="/url", tags=["urls"])

@router.get("")
async def fetch_all_urls(db: AsyncSession = Depends(get_db)):
    return await url_service.fetch_all_url(db)

@router.post(
    "",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shortened URL"
)
async def create_short_url(
    url_in: URLCreate,
    db: AsyncSession = Depends(get_db)
) -> URLResponse:
    """
    Accepts a long URL, generates a unique short code for it (Approach A:
    random base62 + collision retry — see url_service.create_short_url),
    and returns the persisted record.

    Request/response validation is handled entirely by the URLCreate /
    URLResponse Pydantic models — by the time url_in reaches this
    function, FastAPI has already confirmed original_url meets the
    min_length constraint. This endpoint stays thin on purpose: it has
    no business logic of its own, it just wires the HTTP layer to the
    service layer.
    """

    return await url_service.generate_short_url(db, url_in)