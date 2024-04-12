# import pytest
# from modules.db import SqliteDb
# from models.pydantic_models import DbDoctorToCreate


# @pytest.mark.parametrize("a, b, c", [("1", "2", "3")])
# def test_good_hash_len(a, b, c):
#     doctor = DbDoctorToCreate(doctorId=a, specialtyId=b, hospitalId=c)
#     hash = SqliteDb.get_doctor_hash(doctor)
#     assert isinstance(hash, str)
#     assert len(hash) == 20
