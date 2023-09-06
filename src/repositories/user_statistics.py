from sqlalchemy import insert

from db.db import async_session_maker
from models.user_statistics import UserStatistic
from repositories.abstract import SQLAlchemyRepository


class UserStatisticRepository(SQLAlchemyRepository):
    model = UserStatistic

    async def add_one(self, **kwargs) -> int:
        async with async_session_maker() as session:
            stmt = insert(self.model).values(**kwargs).returning(self.model.id)
            res = await session.execute(stmt)
            await session.commit()
            return res.scalar_one()
