from repositories.user_statistics import UserStatisticRepository


class UserStatisticService:
    def __init__(self):
        self.repo: UserStatisticRepository = UserStatisticRepository()

    async def add_outgoing(self, device_id: str, app_name: str, tokens: int, type_query: str, chat_model: str):
        print("add record")
        record_id = await self.repo.add_one(
            device_id=device_id,
            app_name=app_name,
            tokens=tokens,
            type_query=type_query,
            chat_model=chat_model,
            type="outgoing"
        )
        return record_id

    async def add_incoming(self, device_id: str, app_name: str, type_query: str, chat_model: str):
        record_id = await self.repo.add_one(
            device_id=device_id,
            app_name=app_name,
            type="incoming",
            chat_model=chat_model,
            type_query=type_query
        )
        return record_id
