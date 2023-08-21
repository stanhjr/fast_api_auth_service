import os

from fastapi import (
    HTTPException,
)
CHAT_GPT_TOKEN = os.getenv("CHAT_GPT_TOKEN")

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


class HeadersService:

    def __init__(self, headers: dict):
        self.headers = headers
        self.modify_headers = headers.copy()

    def is_valid(self) -> bool:
        device_id = self.headers.get("device-id")
        auth_token = self.headers.get("authorization")
        type_query = self.headers.get("type-query")
        if not device_id or not auth_token or not type_query:
            return False
        return True

    def get_modify_headers(self) -> dict:
        self.modify_headers["host"] = "api.openai.com"
        self.modify_headers.pop("device-id", None)
        self.modify_headers.pop("type-query", None)
        self.modify_headers.pop("authorization", None)
        self.modify_headers["Authorization"] = f"Bearer {CHAT_GPT_TOKEN}"
        return self.modify_headers

    def get_device_id(self) -> str:
        return self.headers.get("device-id")

    def get_auth_token(self) -> str:
        return self.headers.get("authorization")

    def get_type_query(self) -> str:
        return self.headers.get("type-query")
