from depends import sqlite_db as db
from gorzdrav.api import Gorzdrav
from gorzdrav.models import ApiAppointment

lst = db.get_active_doctors_joined_users()
for key, value in lst.items():
    print(value, end="\n")
    appointments: list[ApiAppointment] = Gorzdrav.get_appointments(
        lpuId=value.lpuId, doctorId=value.doctorId
    )
    print(*appointments, end="\n")
    print(len(appointments))
