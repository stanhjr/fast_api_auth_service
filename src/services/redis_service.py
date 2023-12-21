import os

import aioredis
from fastapi import HTTPException

from schemas.headers import TypeModelEnum, TypeQueryEnum
from tools import send_telegram_alert


class RedisService:
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    LIMIT_TOKENS_3 = int(os.getenv("LIMIT_TOKENS_3"))
    LIMIT_TOKENS_4 = int(os.getenv("LIMIT_TOKENS_4"))
    BASE_TTL_SECONDS = int(os.getenv("BASE_TTL_SECONDS"))
    EXPIRED_API_KEY_SET_NAME = "expired_api_key_set"
    KASPER_API_KEY = os.getenv("KASPER_API_KEY", "")
    PROMPTS_API_KEY = os.getenv("PROMPTS_API_KEY", "")
    PIC_ANSWER_API_KEY = os.getenv("PIC_ANSWER_API_KEY", "")
    EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")
    CHAT_GPT_MAIN_API_KEYS = set(os.getenv("CHAT_GPT_MAIN_API_KEYS").split(","))

    def __init__(self):
        self.redis = aioredis.from_url(
            f"redis://{self.REDIS_HOST}",
            encoding="utf-8",
            decode_responses=True,
            password=self.REDIS_PASSWORD
        )

    async def get_attempts_number(self, bandl_id: str | None) -> int:
        if bandl_id is None:
            return len(self.CHAT_GPT_MAIN_API_KEYS)
        return len(self.CHAT_GPT_MAIN_API_KEYS) + 1

    async def _get_tokens_by_device_id(self, key: str):
        async with self.redis.client() as conn:
            tokens = await conn.get(key)
            if tokens:
                return int(tokens)
            return None

    async def set_tokens_by_device_id(self, device_id: str, tokens: int, app_name: str, type_model: str) -> int:
        async with self.redis.client() as conn:
            key = f"{app_name}_{device_id}_{type_model}"
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

    async def limit_tokens_exceeded_validation(
            self,
            device_id: str,
            type_model: str,
            app_name: str,
            type_query: str
    ) -> bool:
        if type_query != TypeQueryEnum.chat:
            return True
        key = f"{app_name}_{device_id}_{type_model}"
        tokens_by_device_id = await self._get_tokens_by_device_id(key)
        if not tokens_by_device_id:
            return True

        if type_model == TypeModelEnum.gpt_3 and tokens_by_device_id > self.LIMIT_TOKENS_3:
            raise HTTPException(status_code=400, detail={"message": "Chat GPT-3.5, tokens limit exceeded", "code": 5})
        if type_model == TypeModelEnum.gpt_4 and tokens_by_device_id > self.LIMIT_TOKENS_4:
            raise HTTPException(status_code=400, detail={"message": "Chat GPT-4, tokens limit exceeded", "code": 6})

        return True

    async def set_expired_api_key(self, expired_api_key: str, app_name: str):
        async with self.redis.client() as conn:
            await send_telegram_alert(
                text=f"ATTENTION THIS API KEY EXPIRED {expired_api_key}, APP_NAME -> {app_name}"
            )
            res = await conn.sadd(self.EXPIRED_API_KEY_SET_NAME, expired_api_key)
            return res

    async def _get_expired_api_key_set(self) -> set:
        async with self.redis.client() as conn:
            expired_set = await conn.smembers(self.EXPIRED_API_KEY_SET_NAME)
            if not expired_set:
                return set()
            return expired_set

    async def get_valid_api_key(self, bandl_id: str | None) -> str:
        api_key_set_strategy = {
            "casper.app.com": self.KASPER_API_KEY,
            "com.prompt.promptAI": self.PROMPTS_API_KEY,
            "com.aiChat.picAnswerAI": self.PIC_ANSWER_API_KEY,
            "email.assistant.app.com": self.EMAIL_API_KEY,
        }

        expired_token_set = await self._get_expired_api_key_set()
        app_api_key = api_key_set_strategy.get(bandl_id)
        if app_api_key is not None and app_api_key not in expired_token_set:
            return app_api_key

        result_set = self.CHAT_GPT_MAIN_API_KEYS - expired_token_set

        if not result_set:
            raise HTTPException(status_code=400, detail={"message": "Not Valid APi keys!", "code": 7})
        return list(result_set)[0]
