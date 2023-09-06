import os

import aioredis
from fastapi import HTTPException

from schemas.headers import TypeModelEnum
from tools import send_telegram_alert

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
LIMIT_TOKENS_3 = int(os.getenv("LIMIT_TOKENS_3"))
LIMIT_TOKENS_4 = int(os.getenv("LIMIT_TOKENS_4"))
BASE_TTL_SECONDS = int(os.getenv("BASE_TTL_SECONDS"))
CHAT_GPT_API_KEY_LIST = os.getenv("CHAT_GPT_API_KEY_LIST").split(",")


class RedisService:
    REDIS_HOST = REDIS_HOST
    REDIS_PASSWORD = REDIS_HOST
    LIMIT_TOKENS_3 = LIMIT_TOKENS_3
    LIMIT_TOKENS_4 = LIMIT_TOKENS_4
    EXPIRED_API_KEY_SET_NAME = "expired_api_key_set"
    CHAT_GPT_API_KEY_SET = set(CHAT_GPT_API_KEY_LIST)
    BASE_TTL_SECONDS = BASE_TTL_SECONDS

    def __init__(self):
        self.redis = aioredis.from_url(
            f"redis://{REDIS_HOST}",
            encoding="utf-8",
            decode_responses=True,
            password=REDIS_PASSWORD
        )

    async def _get_tokens_by_device_id(self, key: str):
        async with self.redis.client() as conn:
            tokens = await conn.get(key)
            if tokens:
                return int(tokens)
            return None

    async def set_tokens_by_device_id(self, device_id: str, tokens: int, app_name: str) -> int:
        async with self.redis.client() as conn:
            key = f"{app_name}_{device_id}"
            current_tokens = await self._get_tokens_by_device_id(key)
            if not current_tokens:
                await conn.set(key, tokens)
                await conn.expire(key, self.BASE_TTL_SECONDS)
                return tokens
            current_ttl = await conn.ttl(key)
            current_tokens += tokens
            await conn.set(key, current_tokens)
            await conn.expire(key, current_ttl)
            return current_tokens

    async def limit_tokens_exceeded_validation(self, device_id: str, type_model: str, app_name: str) -> bool:
        key = f"{app_name}_{device_id}"
        tokens_by_device_id = await self._get_tokens_by_device_id(key)
        if not tokens_by_device_id:
            return True

        if type_model == TypeModelEnum.gpt_3 and tokens_by_device_id > self.LIMIT_TOKENS_3:
            raise HTTPException(status_code=400, detail="Chat GPT-3.5, tokens limit exceeded")
        if type_model == TypeModelEnum.gpt_4 and tokens_by_device_id > self.LIMIT_TOKENS_4:
            raise HTTPException(status_code=400, detail="Chat GPT-4, tokens limit exceeded")

        return True

    async def set_expired_api_key(self, expired_api_key: str):
        async with self.redis.client() as conn:
            await send_telegram_alert(text=f"ATTENTION THIS API KEY EXPIRED {expired_api_key}")
            res = await conn.sadd(self.EXPIRED_API_KEY_SET_NAME, expired_api_key)
            return res

    async def _get_expired_api_key_set(self) -> set:
        async with self.redis.client() as conn:
            expired_set = await conn.smembers(self.EXPIRED_API_KEY_SET_NAME)
            if not expired_set:
                return set()
            return expired_set

    async def get_valid_api_key(self) -> str:
        expired_token_set = await self._get_expired_api_key_set()
        result_set = self.CHAT_GPT_API_KEY_SET - expired_token_set

        if not result_set:
            raise HTTPException(status_code=400, detail="Not Valid APi keys!")
        return list(result_set)[0]
