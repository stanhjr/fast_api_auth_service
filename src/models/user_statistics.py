from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from schemas.enums import Type


class UserStatistic(Base):
    __tablename__ = "users_statistic"
    device_id: Mapped[str] = mapped_column()
    app_name: Mapped[str] = mapped_column()
    type_query: Mapped[str] = mapped_column()
    tokens: Mapped[int | None]
    type: Mapped[Type] = mapped_column(default=Type.outgoing)
    chat_model: Mapped[str]

    def __str__(self):
        return f"User {self.device_id}"
