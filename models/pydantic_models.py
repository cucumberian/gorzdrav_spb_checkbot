from datetime import datetime
from typing import Any
from typing import Optional
from typing import Annotated
from pydantic import BaseModel
from pydantic import Field


LPUIdType = Annotated[int, Field(description="Идентификатор лпу")]


class DbDoctorToCreate(BaseModel):
    lpuId: int
    specialtyId: str
    doctorId: str


class DbDoctor(DbDoctorToCreate):
    id: str


class DbUser(BaseModel):
    id: int
    ping_status: bool | None = False
    doctor_id: str | None = None
    last_seen: datetime | None = None


class ApiResponse(BaseModel):
    result: Any | None = None
    success: bool
    errorCode: int
    message: str | None = None
    stackTrace: Any | None = None
    requestId: str | None = None


class ApiDistrict(BaseModel):
    id: str
    name: str


class ApiLPU(BaseModel):
    id: int
    address: str | None = None
    lpuFullName: str | None = None


class ApiSpecialty(BaseModel):
    id: str
    name: str | None = None
    countFreeParticipant: int | None = None
    countFreeTicket: int | None = None
    lastDate: datetime | None = None
    nearestDate: datetime | None = None


class ApiDoctor(BaseModel):
    id: str
    name: str
    freeParticipantCount: int = 0
    freeTicketCount: int = 0
    lastDate: datetime | None
    nearestDate: datetime | None
    ariaNumber: str | None

    def __str__(self) -> str:
        return (
            f"Врач: {self.name}, "
            + f"талонов: {self.freeTicketCount}, "
            + f"мест: {self.freeParticipantCount}."
        )

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def have_free_tickets(self) -> bool:
        return self.freeTickerCount > 0

    @property
    def have_free_places(self) -> bool:
        return self.freeParticipantCount > 0

    @property
    def is_free(self) -> bool:
        return self.have_free_tickets or self.have_free_places


class Doctor(ApiDoctor):
    districtId: Optional[str]
    lpuId: int
    specialtyId: str

    @property
    def link(self) -> str:
        district_id = self.districtId or ""
        return f"https://gorzdrav.spb.ru/service-free-schedule#%5B\
            %7B%22district%22:%22{district_id}%22%7D,\
            %7B%22lpu%22:%22{self.lpuId}%22%7D,\
            %7B%22speciality%22:%22{self.specialtyId}%22%7D,\
            %7B%22schedule%22:%22{self.id}%22%7D,\
            %7B%22doctor%22:%22{self.id}%22%7D%5D"


class ApiAppointment(BaseModel):
    id: str
    visitStart: datetime | None
    visitEnd: datetime | None
    # address: str?
    # number: str?
    room: str | None


class ApiTimetable(BaseModel):
    appointments: list[ApiAppointment]
    denyCause: str | None = Field(description="Занят / Свободен")
    recordableDay: bool
    visitStart: datetime | None
    visitEnd: datetime | None
