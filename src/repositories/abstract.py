from uuid import UUID

from sqlalchemy import (
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyRepository:
    model = None

    def __init__(self, session: AsyncSession = None):
        self.session = session

    async def add_one(self, data: dict) -> int:
        stmt = insert(self.model).values(**data).returning(self.model.id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.scalar_one()

    async def get_by_id(self, model_id: UUID):
        stmt = select(self.model).where(
            self.model.is_deleted.is_(False),
            self.model.id == model_id
        )
        res = await self.session.execute(stmt)
        row = res.fetchone()
        if row is not None:
            return row[0]

    async def delete_one(self, model_id: UUID):
        stmt = select(self.model).where(self.model.id == model_id).with_for_update()
        await self.session.execute(stmt)
        stmt = (
            update(self.model).
            where(self.model.id == model_id).
            values(is_deleted=True).
            returning(self.model.id)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.scalar_one()
