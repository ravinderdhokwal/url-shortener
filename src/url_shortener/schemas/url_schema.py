from pydantic import BaseModel, ConfigDict, Field


class URLRequestSchema(BaseModel):
    original_url: str = Field(min_length=10)

class URLResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_code: str
    original_url: str
    is_active: bool