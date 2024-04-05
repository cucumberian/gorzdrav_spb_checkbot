import pytest
from modules.db import SqliteDb
from modules.models import DoctorToCreate


@pytest.mark.parametrize("a, b, c", [("1", "2", "3")])
def test_good_hash_len(a, b, c):
    doctor = DoctorToCreate(doctor_id=a, speciality_id=b, hospital_id=c)
    hash = SqliteDb.get_doctor_hash(doctor)
    assert isinstance(hash, str)
    assert len(hash) == 20
