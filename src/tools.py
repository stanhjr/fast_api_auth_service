import os

import aiohttp
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from schemas.headers import HeadersModel

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CHAT_GPT_API_KEY_LIST: list = os.getenv("CHAT_GPT_API_KEY_LIST").split(",")


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
        raise HTTPException(status_code=400, detail="Not valid type query")

    return url


async def get_response(url: str, content, headers_service, redis_service):
    for attempts in range(len(CHAT_GPT_API_KEY_LIST)):
        valid_api_key = await redis_service.get_valid_api_key()
        headers_service.set_api_key(valid_api_key=valid_api_key)
        headers = headers_service.get_modify_headers()
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers, data=content) as resp:
                response_content = await resp.json()
                json_data = jsonable_encoder(response_content)
                response = CustomResponse(
                    headers=dict(resp.headers),
                    content=json_data,
                    status_code=resp.status
                )

                if response.status_code == 401 and response.content["error"]["code"] == "invalid_api_key":
                    await redis_service.set_expired_api_key(expired_api_key=headers_service.valid_api_key)
                else:
                    return response
    await send_telegram_alert(text="ATTENTION ALL API KEYS EXPIRED")


class HeadersService:

    def __init__(self, headers: dict):
        self.headers = headers
        self.modify_headers = headers.copy()
        self.valid_api_key = None

    def is_valid(self) -> bool:
        try:
            HeadersModel(
                device_id=self.headers.get("device-id"),
                authorization=self.headers.get("authorization"),
                app_name=self.headers.get("app-name"),
                type_model=self.headers.get("type-model"),
                type_query=self.headers.get("type-query"),
            )
        except ValueError as e:
            print(e)
            return False
        return True

    def get_modify_headers(self) -> dict:
        self.modify_headers["host"] = "api.openai.com"
        self.modify_headers.pop("device-id", None)
        self.modify_headers.pop("type-query", None)
        self.modify_headers.pop("type-model", None)
        self.modify_headers.pop("authorization", None)
        self.modify_headers.pop("app-name", None)
        self.modify_headers.pop("postman-token", None)
        self.modify_headers["Content-Type"] = "application/json; charset=utf8"
        self.modify_headers.pop("Accept-Encoding", None)
        self.modify_headers["Accept-Encoding"] = "deflate"
        self.modify_headers["charset"] = "utf-8"

        return self.modify_headers

    def set_api_key(self, valid_api_key: str):
        self.valid_api_key = valid_api_key
        self.modify_headers["Authorization"] = f"Bearer {valid_api_key}"

    def get_device_id(self) -> str:
        return self.headers.get("device-id")

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
