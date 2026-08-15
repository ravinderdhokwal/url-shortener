from pydantic import BaseModel, Field


class URLCreate(BaseModel):
    original_url: str = Field(min_length=10)

class URLResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    is_active: bool