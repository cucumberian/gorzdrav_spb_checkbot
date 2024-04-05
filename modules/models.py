from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .net import GorzdravSpbAPI


class DbDoctorToCreate(BaseModel):
    doctor_id: str
    speciality_id: str
    hospital_id: str


class DbDoctor(DbDoctorToCreate):
    id: str


class DbUser(BaseModel):
    id: int
    ping_status: Optional[bool] = False
    doctor_id: Optional[str] = None
    last_seen: Optional[datetime] = None


class ApiDistrict(BaseModel):
    id: str
    name: str


class ApiHospital(BaseModel):
    id: int | str
    districtId: Optional[int | str]


class ApiSpeciality(BaseModel):
    id: str | int
    name: Optional[str]
    countFreeParticipant: Optional[int]
    countFreeTicket: Optional[int]
    lastDate: Optional[datetime]
    nearestDate: Optional[datetime]


class ApiDoctor(BaseModel):
    id: str
    name: Optional[str]
    freeParticipantCount: int = 0
    freeTicketCount: int = 0
    lastDate: Optional[datetime]
    nearestDate: Optional[datetime]


class Doctor(ApiDoctor):
    doctor_id: str
    speciality_id: str
    hospital_id: str
    districtId: Optional[str]

    def __str__(self):
        return (
            f"врач {self.name}"
            + f" талонов: {self.freeTicketCount},"
            + f" мест для записи: {self.freeParticipantCount}"
        )

    def __repr__(self):
        return self.__str__()

    @property
    def is_free(self):
        return self.freeParticipantCount > 0 or self.freeTicketCount > 0

    @property
    def link(self):
        district_id = self.districtId or ""
        return f"https://gorzdrav.spb.ru/service-free-schedule#%5B\
            %7B%22district%22:%22{district_id}%22%7D,\
            %7B%22lpu%22:%22{self.hospital_id}%22%7D,\
            %7B%22speciality%22:%22{self.speciality_id}%22%7D,\
            %7B%22schedule%22:%22{self.id}%22%7D,\
            %7B%22doctor%22:%22{self.id}%22%7D%5D"

    def update(self):
        doc = GorzdravSpbAPI().get_doctor()
        