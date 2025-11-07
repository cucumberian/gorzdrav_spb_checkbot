from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class DbDoctorToCreate(BaseModel):
    districtId: str
    lpuId: int
    specialtyId: str
    doctorId: str


class DbDoctor(DbDoctorToCreate):
    id: str


class DbUser(BaseModel):
    id: int
    ping_status: bool | None = False
    doctor_id: Optional[str] = None
    last_seen: Optional[datetime] = None
    limit_days: Optional[int] = None


class DbDoctorWithUsers(DbDoctor):
    pinging_users: list[DbUser]
