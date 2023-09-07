from enum import Enum

from pydantic import BaseModel


class TypeQueryEnum(str, Enum):
    chat = "chat"
    moderation = "moderation"
    generation = "generation"


class TypeModelEnum(str, Enum):
    gpt_3 = "gpt-3.5-turbo"
    gpt_4 = "gpt-4"


class HeadersModel(BaseModel):
    device_id: str
    authorization: str
    type_query: TypeQueryEnum
    type_model: TypeModelEnum | None
    app_name: str


class HeadersStatisticsModel(BaseModel):
    device_id: str
    authorization: str
    type_query: TypeQueryEnum
    app_name: str
