from pydantic import BaseModel

from schemas.headers import TypeModelEnum


class StatisticsData(BaseModel):
    device_id: str
    app_name: str
    word_list: list[str]
    type_model: TypeModelEnum
