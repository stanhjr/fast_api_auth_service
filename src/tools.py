import os

import aiohttp
import tiktoken
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from schemas.headers import (
    HeadersModel,
    HeadersStatisticsModel,
    OldHeadersModel,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


async def send_telegram_alert(text: str):
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            if response.status == 200:
                return response


def get_url(type_query: str) -> str:
    type_url = {
        "chat": "https://api.openai.com/v1/chat/completions",
        "moderation": "https://api.openai.com/v1/moderations",
        "generation": "https://api.openai.com/v1/images/generations",
    }
    url = type_url.get(type_query)
    if url is None:
        raise HTTPException(status_code=403, detail={"message": "Not valid type query", "code": 2})

    return url


class HeadersService:

    def __init__(self, headers: dict):
        self.headers = headers
        self.modify_headers = headers.copy()
        self.valid_api_key = None

    def is_valid_statistics(self) -> bool:
        try:
            HeadersStatisticsModel(
                device_id=self.headers.get("device-id"),
                authorization=self.headers.get("authorization"),
                app_name=self.headers.get("app-name"),
                type_query=self.headers.get("type-query"),
            )
        except ValueError:
            return False
        return True

    def is_old_valid(self) -> bool:
        try:
            OldHeadersModel(
                device_id=self.headers.get("device-id"),
                authorization=self.headers.get("authorization"),
                app_name=self.headers.get("app-name"),
                type_model=self.headers.get("type-model"),
                type_query=self.headers.get("type-query"),
            )
        except ValueError:
            return False
        return True

    def is_valid(self) -> bool:
        try:
            HeadersModel(
                device_id=self.headers.get("device-id"),
                authorization=self.headers.get("authorization"),
                app_name=self.headers.get("app-name"),
                type_model=self.headers.get("type-model"),
                type_query=self.headers.get("type-query"),
                bandl_id=self.headers.get("bandl-id"),
            )
        except ValueError as e:
            return False
        return True

    def get_modify_headers(self) -> dict:
        self.modify_headers["host"] = "api.openai.com"
        self.modify_headers.pop("device-id", None)
        self.modify_headers.pop("type-query", None)
        self.modify_headers.pop("type-model", None)
        self.modify_headers.pop("authorization", None)
        self.modify_headers.pop("app-name", None)
        self.modify_headers.pop("bandl-id", None)
        return self.modify_headers

    def set_api_key(self, valid_api_key: str):
        self.valid_api_key = valid_api_key
        self.modify_headers["Authorization"] = f"Bearer {valid_api_key}"

    def get_device_id(self) -> str:
        return self.headers.get("device-id")

    def get_bandl_id(self) -> str:
        return self.headers.get("bandl-id")

    def get_app_name(self) -> str:
        return self.headers.get("app-name")

    def get_auth_token(self) -> str:
        return self.headers.get("authorization")

    def get_type_query(self) -> str:
        return self.headers.get("type-query")

    def get_type_model(self) -> str:
        return self.headers.get("type-model")


class CustomResponse:

    def __init__(self, headers: dict, content: dict, status_code: int):
        self.headers = headers
        self.content = content
        self.status_code = status_code

    def get_tokens_number(self) -> int:
        try:
            return int(self.content["usage"]["total_tokens"])
        except Exception:
            return 0
