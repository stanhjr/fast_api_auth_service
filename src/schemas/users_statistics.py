from pydantic import BaseModel


class UsersStatisticsSchemaAdd(BaseModel):
    device_id: str
    app_name: str
