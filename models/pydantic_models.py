from datetime import datetime
from typing import Any
from typing import Annotated
from pydantic import BaseModel
from pydantic import Field


LPUIdType = Annotated[int, Field(description="Идентификатор лпу")]


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
    name: str
    countFreeParticipant: int
    countFreeTicket: int
    lastDate: datetime | None = None
    nearestDate: datetime | None = None


class ApiDoctor(BaseModel):
    id: str
    name: str
    freeParticipantCount: int
    freeTicketCount: int
    lastDate: datetime | None
    nearestDate: datetime | None
    ariaNumber: str | None

    def __str__(self) -> str:
        return (
            f"Врач: {self.name}, "
            + f"талонов: {self.freeTicketCount}, "
            + f"мест: {self.freeParticipantCount}."
        )

    @property
    def have_free_tickets(self) -> bool:
        return self.freeTickerCount > 0

    @property
    def have_free_places(self) -> bool:
        return self.freeParticipantCount > 0


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
