from pydantic import BaseModel, ConfigDict, Field


class URLCreate(BaseModel):
    original_url: str = Field(min_length=10)

class URLResponse(BaseModel):
    # Lets Pydantic build this model by reading attributes off an object
    # (the SQLAlchemy URLModel instance) rather than requiring a dict —
    # necessary because the endpoint returns url_service's URLModel
    # directly and FastAPI serializes it through this schema.
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_code: str
    original_url: str
    is_active: bool