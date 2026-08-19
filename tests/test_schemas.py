import pytest
from pydantic import ValidationError

from url_shortener.schemas.url_schema import URLRequestSchema, URLResponseSchema


def test_request_schema_requires_min_length():
    with pytest.raises(ValidationError):
        URLRequestSchema(original_url="too-short")


def test_request_schema_accepts_valid_url():
    schema = URLRequestSchema(original_url="https://example.com")
    assert schema.original_url == "https://example.com"


def test_response_schema_from_attributes():
    class Row:
        short_code = "abc1234"
        original_url = "https://example.com/x"
        is_active = True

    schema = URLResponseSchema.model_validate(Row())
    assert schema.model_dump() == {
        "short_code": "abc1234",
        "original_url": "https://example.com/x",
        "is_active": True,
    }
