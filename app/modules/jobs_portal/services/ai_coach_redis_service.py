import json
import logging
from typing import Any, Dict, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2.0,
            )
            await _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed for AI Coach: {e}")
            _redis_client = None
    return _redis_client


class AICoachRedisService:
    @staticmethod
    def _key(session_id: str) -> str:
        return f"ai_coach:session:{session_id}"

    @classmethod
    async def save_session(cls, session_id: str, data: Dict[str, Any], ttl: int = 86400) -> bool:
        r = await get_redis()
        if not r:
            return False
        try:
            await r.setex(cls._key(session_id), ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.warning(f"Failed to save AI Coach session to Redis: {e}")
            return False

    @classmethod
    async def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        r = await get_redis()
        if not r:
            return None
        try:
            raw = await r.get(cls._key(session_id))
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Failed to get AI Coach session from Redis: {e}")
        return None

    @classmethod
    async def append_chat_message(cls, session_id: str, message_obj: Dict[str, Any]) -> bool:
        session_data = await cls.get_session(session_id)
        if not session_data:
            return False
        
        chat_history = session_data.get("chat_history", [])
        chat_history.append(message_obj)
        session_data["chat_history"] = chat_history
        
        return await cls.save_session(session_id, session_data)

    @classmethod
    async def delete_session(cls, session_id: str) -> bool:
        r = await get_redis()
        if not r:
            return False
        try:
            await r.delete(cls._key(session_id))
            return True
        except Exception as e:
            logger.warning(f"Failed to delete AI Coach session from Redis: {e}")
            return False
