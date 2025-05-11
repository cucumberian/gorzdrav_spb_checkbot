import pytest
import os
import random
import datetime
from db.sqlite_db import SqliteDb
from models import pydantic_models

# generate random name for db
random_name = str(random.randint(10_000_000, 99_999_999))
TEST_DB = f"{random_name}.db"


@pytest.fixture(autouse=True, scope="function")
def create_db(request):
    SqliteDb(TEST_DB)
    yield
    os.remove(TEST_DB)


@pytest.mark.parametrize(
    "user_id, ping_status, doctor_id, last_seen",
    [
        (1, None, None, datetime.datetime.now()),
        (2, None, None, datetime.datetime.now(datetime.UTC)),
        (0, None, None, datetime.datetime.strptime("2020-01-01", "%Y-%m-%d")),
        (1, True, None, None),
        (-1, None, None, datetime.datetime.now()),
        (1, True, None, datetime.datetime.now()),
        (1, False, None, datetime.datetime.now()),
        (1, None, "123", datetime.datetime.now()),
        (11231241123, True, "123", datetime.datetime.now()),
        (1, False, "123", datetime.datetime.now(datetime.UTC)),
    ],
)
def test_add_user(
    user_id: int,
    ping_status: bool | None,
    doctor_id: str | None,
    last_seen: datetime,
):
    db = SqliteDb(TEST_DB)
    new_user = pydantic_models.DbUser(
        id=user_id,
        ping_status=ping_status,
        doctor_id=doctor_id,
        last_seen=last_seen,
    )
    db.add_user(new_user)
    db_user = db.get_user(user_id)

    assert db_user == new_user
    if ping_status is None:
        assert db_user.ping_status is False
    else:
        assert db_user.ping_status == ping_status

    assert db_user.doctor_id == doctor_id
    if last_seen is None:
        delta_time = datetime.timedelta(milliseconds=50)
        assert (
            db_user.last_seen - datetime.datetime.now(datetime.UTC)
        ) < delta_time
    else:
        assert db_user.last_seen == last_seen


@pytest.mark.parametrize(
    "districtId, lpuId, specialtyId, doctorId",
    [
        ("0", 1, "2", "3"),
        ("district", 0, "1231", "000"),
        ("район3123.4", -31231, "word", "docid"),
        ("-1", 1, "специальность", "ид доктора"),
    ],
)
def test_add_doctor(
    districtId: str, lpuId: int, specialtyId: str, doctorId: str
):
    db = SqliteDb(TEST_DB)
    new_doctor = pydantic_models.DbDoctorToCreate(
        districtId=districtId,
        lpuId=lpuId,
        specialtyId=specialtyId,
        doctorId=doctorId,
    )
    db_doctor_id = db.add_doctor(new_doctor)
    db_doctor = db.get_doctor(doctor_id=db_doctor_id)

    assert db_doctor.doctorId == doctorId
    assert db_doctor.lpuId == lpuId
    assert db_doctor.specialtyId == specialtyId


@pytest.mark.parametrize(
    "user_id, ping_status, expectation",
    [
        (1, True, True),
        (2, False, False),
        (0, None, False),
    ],
)
def test_get_ping_status(
    user_id: int,
    ping_status: bool,
    expectation: bool,
):
    db = SqliteDb(TEST_DB)
    new_user = pydantic_models.DbUser(
        id=user_id,
        ping_status=ping_status,
    )
    db.add_user(user=new_user)
    db_user = db.get_user(user_id=user_id)
    assert db_user.ping_status == expectation


@pytest.mark.parametrize(
    "ping_status, expected_result",
    [(True, True), (False, False)],
)
def test_set_user_ping_status(ping_status: bool, expected_result: bool):
    pass
    user_id = random.randint(0, 1000000)
    new_user = pydantic_models.DbUser(
        id=user_id,
    )
    db = SqliteDb(TEST_DB)
    db.add_user(user=new_user)
    db.set_user_ping_status(user_id=user_id, ping_status=ping_status)
    db_user = db.get_user(user_id=user_id)
    assert db_user.ping_status == expected_result
    db.set_user_ping_status(user_id=user_id, ping_status=not ping_status)
    db_user = db.get_user(user_id=user_id)
    assert db_user.ping_status != expected_result


@pytest.mark.parametrize(
    "user_id, districtId, lpuId, specialtyId, doctorId",
    [
        (1, "1", 2, "3", "4"),
        (0, "0", 0, "три", "два"),
    ],
)
def test_get_user_doctor(
    user_id: int, districtId: str, lpuId: int, specialtyId: str, doctorId: str
):
    db = SqliteDb(TEST_DB)
    new_user = pydantic_models.DbUser(id=user_id)
    new_doctor = pydantic_models.DbDoctorToCreate(
        districtId=districtId,
        lpuId=lpuId,
        specialtyId=specialtyId,
        doctorId=doctorId,
    )
    db.add_user(user=new_user)
    doctor_id: str = db.add_doctor(doctor=new_doctor)
    db.add_user_doctor(user_id=user_id, doctor_id=doctor_id)
    db_user = db.get_user(user_id=user_id)
    db_doctor = db.get_user_doctor(user_id=user_id)
    assert db_user.doctor_id == doctor_id
    assert db_doctor.id == db_user.doctor_id
    assert db_doctor.districtId == districtId
    assert db_doctor.lpuId == lpuId
    assert db_doctor.specialtyId == specialtyId
    assert db_doctor.doctorId == doctorId


def test_delete_user():
    db = SqliteDb(TEST_DB)
    user_id = random.randint(0, 1000000)
    new_user = pydantic_models.DbUser(id=user_id)
    db.add_user(new_user)
    db.delete_user(user_id=user_id)
    assert db.get_user(user_id=user_id) is None


@pytest.mark.parametrize(
    "last_seen",
    [
        (datetime.datetime.now(datetime.UTC)),
        (None),
        (
            datetime.datetime.strptime(
                "2020-01-01 03:04:05", "%Y-%m-%d %H:%M:%S"
            )
        ),
    ],
)
def test_update_user_time(last_seen):
    user_id = 1
    initial_timestamp = datetime.datetime.strptime("2000-01-01", "%Y-%m-%d")
    new_user = pydantic_models.DbUser(id=user_id, last_seen=initial_timestamp)
    db = SqliteDb(TEST_DB)
    db.add_user(new_user)
    db_user = db.get_user(user_id=user_id)
    assert db_user.last_seen == initial_timestamp
    db.update_user_time(user_id=user_id, last_seen=last_seen)
    db_user = db.get_user(user_id=user_id)
    if last_seen is None:
        timedelta = datetime.timedelta(milliseconds=50)
        current_time = datetime.datetime.now(datetime.UTC)
        assert (db_user.last_seen - current_time) < timedelta
    else:
        assert db_user.last_seen == last_seen


@pytest.mark.parametrize(
    "n_users, n_doctors",
    [(10, 10), (1, 10), (0, 0), (0, 10), (10, 0), (10, 1), (100, 100)],
)
def test_get_active_doctors(
    n_users: int,
    n_doctors: int,
):
    db = SqliteDb(TEST_DB)

    users_data = [(i, bool(random.randint(0, 1))) for i in range(n_users)]
    doctors_data = [
        (f"distr{i}", i, f"spec{i}", f"dic{i}") for i in range(n_doctors)
    ]
    doctor_ids = set()
    for doctor_data in doctors_data:
        new_doctor = pydantic_models.DbDoctorToCreate(
            districtId=doctor_data[0],
            lpuId=doctor_data[1],
            specialtyId=doctor_data[2],
            doctorId=doctor_data[3],
        )
        doctor_id = db.add_doctor(new_doctor)
        doctor_ids.add(doctor_id)

    for user_data in users_data:
        new_user = pydantic_models.DbUser(
            id=user_data[0],
            ping_status=user_data[1],
        )
        db.add_user(new_user)
        if doctor_ids:
            random_doctor_id = random.choice(list(doctor_ids))
            db.add_user_doctor(user_id=user_data[0], doctor_id=random_doctor_id)
    active_doctors = db.get_active_doctors()
    active_user_doctors = set()
    for user_data in users_data:
        if user_data[1]:
            db_user = db.get_user(user_data[0])
            if db_user.doctor_id is None:
                continue
            active_user_doctors.add(db_user.doctor_id)
            assert db_user.doctor_id in [d.id for d in active_doctors]
    assert len(active_user_doctors) == len(active_doctors)


# def test_get_users_by_doctor():
#     db = SqliteDb(TEST_DB)
#     timestamp = datetime.now()
#     users_num = random.randint(5, 10)
#     users = [User(id=i, last_seen=timestamp) for i in range(users_num)]
#     doctor = DoctorToCreate(
#         doctor_id=str(random.random()),
#         speciality_id=str(random.random()),
#         hospital_id=str(random.random()),
#     )
#     # для каждого пользователя есть доктор
#     doctor_id = db.add_doctor(doctor)
#     users_has_doctor = [bool(random.randint(0, 1)) for i in range(users_num)]

#     for user_index, user in enumerate(users):
#         db.add_user(user)
#         if users_has_doctor[user_index]:
#             db.add_user_doctor(user_id=user.id, doctor_id=doctor_id)

#     selected_users: list[User] = db.get_users_by_doctor(doctor_id=doctor_id)
#     for user_index, user in enumerate(users):
#         if users_has_doctor[user_index]:
#             assert user.id in [u.id for u in selected_users]
#         else:
#             assert user.id not in [u.id for u in selected_users]
