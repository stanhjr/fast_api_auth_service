import uuid
from datetime import datetime

from sqlalchemy import UUID, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    id: Mapped[uuid.uuid4] = mapped_column(UUID(as_uuid=True),
                                           primary_key=True,
                                           default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self):
        return str(self)
