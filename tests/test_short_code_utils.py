import string

from url_shortener.core.config import settings
from url_shortener.utils.short_code_utils import generate_short_code

_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


def test_generate_short_code_uses_configured_length():
    code = generate_short_code()
    assert len(code) == settings.DEFAULT_SHORT_CODE_LENGTH


def test_generate_short_code_is_base62():
    code = generate_short_code()
    assert set(code).issubset(set(_ALPHABET))


def test_generate_short_code_is_not_constant():
    codes = {generate_short_code() for _ in range(20)}
    assert len(codes) > 1
