import pytest
import os
import random
from datetime import datetime
from modules.db import SqliteDb
from models.models import User
from models.models import Doctor
from models.models import DoctorToCreate


TEST_DB = "test.db"


@pytest.fixture(autouse=True, scope="function")
def create_db(request):
    SqliteDb(TEST_DB)
    yield
    os.remove(TEST_DB)


@pytest.mark.parametrize(
    "user_id, ping_status, doctor_id, timestamp",
    [
        (1, None, None, datetime.now()),
        (2, None, None, datetime.now()),
        (0, None, None, datetime.strptime("2020-01-01", "%Y-%m-%d")),
        (-1, None, None, datetime.now()),
        (1, True, None, datetime.now()),
        (1, False, None, datetime.now()),
        (1, None, "123", datetime.now()),
        (1, True, "123", datetime.now()),
        (1, False, "123", datetime.now()),
    ],
)
def test_add_user(
    user_id: int,
    ping_status: bool | None,
    doctor_id: str | None,
    timestamp: datetime,
):
    db = SqliteDb(TEST_DB)
    user = User(
        id=user_id,
        ping_status=ping_status,
        doctor_id=doctor_id,
        last_seen=timestamp,
    )
    db.add_user(user)
    db_user = db.get_user(user_id)
    assert db_user == user
    assert db_user.ping_status == ping_status
    assert db_user.doctor_id == doctor_id
    assert db_user.last_seen == timestamp


@pytest.mark.parametrize(
    "doc_id, spec_id, hos_id",
    [("1", "2", "3"), ("asdasd", "1231", "000")],
)
def test_add_doctor(doc_id: str, spec_id: str, hos_id: str):
    db = SqliteDb(TEST_DB)
    doc = DoctorToCreate(
        doctor_id=doc_id, speciality_id=spec_id, hospital_id=hos_id
    )
    doc_hash = db.add_doctor(doc)
    doctor_hash = SqliteDb.get_doctor_hash(doc)
    doctor = Doctor(
        id=doctor_hash,
        doctor_id=doc_id,
        speciality_id=spec_id,
        hospital_id=hos_id,
    )
    assert doctor_hash == doc_hash
    assert doctor == db.get_doctor(doctor_hash)


@pytest.mark.parametrize(
    "id, ping_status, timestamp",
    [
        (1, True, datetime.now()),
        (2, False, datetime.now()),
    ],
)
def test_get_user_ping_status(id: int, ping_status: int, timestamp: datetime):
    db = SqliteDb(TEST_DB)
    user = User(id=id, ping_status=ping_status, last_seen=timestamp)
    db.add_user(user)
    user_db = db.get_user(user_id=id)
    assert user_db.ping_status == ping_status


@pytest.mark.parametrize("id, ping_status", [(1, True), (2, False)])
def test_set_user_ping_status(id: int, ping_status: bool):
    db = SqliteDb(TEST_DB)
    timestamp = datetime.now()
    user = User(id=id, ping_status=ping_status, last_seen=timestamp)
    db.add_user(user)
    assert db.get_user_ping_status(user_id=id) == ping_status
    db.set_user_ping_status(user_id=id, ping_status=True)
    assert db.get_user_ping_status(user_id=id)
    db.set_user_ping_status(user_id=id, ping_status=False)
    assert not db.get_user_ping_status(user_id=id)
    db.set_user_ping_status(user_id=id, ping_status=True)
    db.clear_user_ping(user_id=id)
    assert not db.get_user_ping_status(user_id=id)


@pytest.mark.parametrize(
    "user_id, doctor_id, speciality_id, hospital_id",
    [
        (1, "1", "2", "3"),
        (2, "2", "3", "4"),
    ],
)
def test_get_user_doctor(
    user_id: int, doctor_id: str, speciality_id: str, hospital_id: str
):
    db = SqliteDb(TEST_DB)
    timestamp = datetime.now()
    user = User(id=user_id, last_seen=timestamp)
    doc = DoctorToCreate(
        doctor_id=doctor_id,
        speciality_id=speciality_id,
        hospital_id=hospital_id,
    )
    db.add_user(user)
    doc_id = db.add_doctor(doc)
    db.add_user_doctor(user_id=user_id, doctor_id=doc_id)
    doctor = db.get_doctor(doc_id)
    user_doctor = db.get_user_doctor(user_id=user_id)
    assert doctor == user_doctor


def test_get_user_doctor_empty():
    db = SqliteDb(TEST_DB)
    user_id = 1
    timestamp = datetime.now()
    user = User(id=user_id, last_seen=timestamp)
    db.add_user(user)
    doctor = db.get_user_doctor(user_id=1)
    assert doctor is None
    doctor2 = db.get_user_doctor(user_id=2)
    assert doctor2 is None


def test_del_user():
    db = SqliteDb(TEST_DB)
    user_id = 1
    timestamp = datetime.now()
    user = User(id=user_id, last_seen=timestamp)
    db.add_user(user)
    db.del_user(user_id=user_id)
    assert db.get_user(user_id=user_id) is None


def test_update_user_time():
    user_id = 1
    timestamp1 = datetime.strptime("2020-01-01", "%Y-%m-%d")
    timestamp2 = datetime.strptime("2020-01-02", "%Y-%m-%d")
    db = SqliteDb(TEST_DB)
    user = User(id=user_id, last_seen=timestamp1)
    db.add_user(user)
    db.update_user_time(user_id=user_id, timestamp=timestamp2)
    user_db = db.get_user(user_id=user_id)
    assert user_db.last_seen == timestamp2


def test_get_active_doctors():
    db = SqliteDb(TEST_DB)
    doctors_data = [
        ("1", "2", "3"),
        ("2", "3", "4"),
        ("3", "4", "5"),
        ("1", "2", "3"),
    ]
    users_data = [(1, None), (2, True), (3, False), (4, True)]
    doctors_hashes = []
    doctors = []
    for doctor_data in doctors_data:
        doctor = DoctorToCreate(
            doctor_id=doctor_data[0],
            speciality_id=doctor_data[1],
            hospital_id=doctor_data[2],
        )
        doctors_hashes.append(db.add_doctor(doctor))
        doctors.append(
            Doctor(
                id=doctors_hashes[-1],
                doctor_id=doctor_data[0],
                speciality_id=doctor_data[1],
                hospital_id=doctor_data[2],
            )
        )

    for index, user_data in enumerate(users_data):
        user = User(id=user_data[0], ping_status=user_data[1])
        db.add_user(user)
        db.add_user_doctor(
            user_id=user_data[0], doctor_id=doctors_hashes[index]
        )

    active_doctors: list[Doctor] = db.get_active_doctors()
    assert doctors[1] in active_doctors
    assert doctors[2] not in active_doctors
    assert doctors[0] in active_doctors
    assert doctors[0] == doctors[3]


def test_get_users_by_doctor():
    db = SqliteDb(TEST_DB)
    timestamp = datetime.now()
    users_num = random.randint(5, 10)
    users = [User(id=i, last_seen=timestamp) for i in range(users_num)]
    doctor = DoctorToCreate(
        doctor_id=str(random.random()),
        speciality_id=str(random.random()),
        hospital_id=str(random.random()),
    )
    # для каждого пользователя есть доктор
    doctor_id = db.add_doctor(doctor)
    users_has_doctor = [bool(random.randint(0, 1)) for i in range(users_num)]

    for user_index, user in enumerate(users):
        db.add_user(user)
        if users_has_doctor[user_index]:
            db.add_user_doctor(user_id=user.id, doctor_id=doctor_id)

    selected_users: list[User] = db.get_users_by_doctor(doctor_id=doctor_id)
    for user_index, user in enumerate(users):
        if users_has_doctor[user_index]:
            assert user.id in [u.id for u in selected_users]
        else:
            assert user.id not in [u.id for u in selected_users]
