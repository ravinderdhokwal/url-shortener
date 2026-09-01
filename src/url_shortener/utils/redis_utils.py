import json
import logging
from url_shortener.db.redis import redis_client
from url_shortener.models import URLModel

logger = logging.getLogger()


_CACHE_KEY_PREFIX = "short_code:"

def get_cache_key(short_code: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{short_code}"

async def set_cached_record(cache_key: str, value: str, ttl_seconds: int) -> None:
    try:
        await redis_client.set(cache_key, value, ex=ttl_seconds)
    except:
        logger.warning("Redis SET failed for key=%s; continuing without caching", cache_key, exc_info=True)

async def get_cached_record(cache_key: str) -> str | None:
    try:
        return await redis_client.get(cache_key)
    except Exception:
        logger.warning("Redis GET failed for key=%s; falling back to database", cache_key, exc_info=True)
        return None

def serialize_url_record(url_object: URLModel) -> str:
    return json.dumps({ "original_url": url_object.original_url })

def deserialize_url_record(raw: str) -> dict:
    return json.loads(raw)