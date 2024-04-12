import datetime
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from db.database import Base

metadata_obj = sa.MetaData()

users_table = sa.Table(
    "users",
    metadata_obj,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("ping_status", sa.Boolean, default=False),
    sa.Column(
        "last_seen",
        sa.DateTime,
        default=sa.func.now,
        onupdate=sa.func.now,
    ),
)


class UserOrm(Base):
    """
    Table "users"
    id: int - telegram id of user
    ping_status: bool - ping or not gorzdrav for user'd doctor
    last_seen: datetime - last time user was in system
    doctor_id: int - id of doctor for user
    doctor: DoctorOrm - doctor for user
    """

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    ping_status: Mapped[bool] = mapped_column(default=False)
    last_seen: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.now(datetime.UTC),
        onupdate=datetime.datetime.now(datetime.UTC),
    )
    doctor_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey(column="doctors.id", ondelete="SET NULL"),
        default=None,
    )
    doctor: Mapped["DoctorOrm"] = relationship(back_populates="users")

    @property
    def ping_status_str(self) -> str:
        return (
            "Статус проверки: "
            + f"{'Включена' if self.ping_status else 'Отключена'}"
        )

    def __repr__(self) -> str:
        return f"""UserOrm ({self.id})"""


class DoctorOrm(Base):
    """
    Таблица "doctors"
    id: int - ид строки
    districtId: str - id района в системе горздрава
    lpuId: int - id медучреждения в системе горздрава
    specialtyId: str - id специальности врача в системе горздрава
    doctorId: str - id врача в системе горздрава
    """

    __tablename__ = "doctors"
    id: Mapped[str] = mapped_column(
        primary_key=True,
    )
    districtId: Mapped[str]
    lpuId: Mapped[int]
    specialtyId: Mapped[str]
    doctorId: Mapped[str]
    users: Mapped[list["UserOrm"]] = relationship(back_populates="doctor")

    def __str__(self) -> str:
        return f"""Врач ({self.lpuId}; {self.specialtyId}; {self.doctorId})"""
