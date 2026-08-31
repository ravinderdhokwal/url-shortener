from pydantic import BaseModel, ConfigDict, Field, computed_field

from url_shortener.core.config import settings


class URLRequestSchema(BaseModel):
    original_url: str = Field(min_length=10)

class URLResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_code: str = Field(exclude=True)

    @computed_field
    @property
    def short_url(self) -> str:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/{self.short_code}"

    original_url: str
    is_active: bool