from datetime import datetime
from typing import Any
from pydantic import BaseModel
from pydantic import Field


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
    ariaNumber: str | None = None


class ApiAppointment(BaseModel):
    id: str
    visitStart: datetime
    visitEnd: datetime
    number: int
    room: str | None


class ApiTimetable(BaseModel):
    appointments: list[ApiAppointment]
    denyCause: str | None = Field(description="Занят / Свободен", default=None)
    recordableDay: bool
    visitStart: datetime | None
    visitEnd: datetime | None


class Doctor(ApiDoctor):
    districtId: str | None = None
    lpuId: int
    specialtyId: str

    @property
    def doctorId(self) -> str:
        return self.id

    def __str__(self) -> str:
        return (
            f"Врач: {self.name}.\n"
            + f"Талонов: {self.freeTicketCount}, "
            + f"мест для записи: {self.freeParticipantCount}."
        )

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def have_free_tickets(self) -> bool:
        """
        Возвращает True, если у врача есть талончики на запись
        """
        return self.freeTicketCount > 0

    @property
    def have_free_places(self) -> bool:
        """
        Возвращает True, если у врача есть свободные места для записи
        """
        return self.freeParticipantCount > 0

    @property
    def is_free(self) -> bool:
        return self.have_free_tickets and self.have_free_places


class LinkParsingResult(BaseModel):
    districtId: str
    lpuId: int
    specialtyId: str
    doctorId: str | None = None
