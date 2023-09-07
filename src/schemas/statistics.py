from pydantic import BaseModel


class StatisticsData(BaseModel):
    device_id: str
    app_name: str
    word_list: list[str]
    type_model: str
