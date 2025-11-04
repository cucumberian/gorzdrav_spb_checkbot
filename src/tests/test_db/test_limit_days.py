import pytest
import random
import os
from core.checker_logic import CheckerApp
from db.sqlite_db import SqliteDb
from gorzdrav.models import Doctor
from models.pydantic_models import DbUser

random_name = str(random.randint(10_000_000, 99_999_999))
TEST_DB = f"test_{random_name}.db"


@pytest.fixture(scope="function")
def test_db(request):
    db = SqliteDb(db_path=TEST_DB)
    yield db
    os.remove(TEST_DB)


@pytest.fixture(scope="function")
def test_user(test_db: SqliteDb):
    new_user = DbUser(id=1)
    test_db.add_user(user=new_user)
    yield new_user
    test_db.delete_user(user_id=1)


def test_default_limit_days(test_db: SqliteDb, test_user: DbUser):
    user = test_db.get_user(user_id=test_user.id)
    assert user is not None
    assert user.id == test_user.id
    assert user.limit_days is None


@pytest.mark.parametrize(
    "limit_days",
    [
        None,
        0,
        1,
        10,
        -1,
        99999999,
        -1111111111,
    ],
)
def test_set_limit_days(
    test_db: SqliteDb,
    test_user: DbUser,
    limit_days: int | None,
):
    test_db.set_limit_days(user_id=test_user.id, limit_days=limit_days)
    user = test_db.get_user(user_id=test_user.id)
    assert user is not None
    assert user.limit_days == limit_days


@pytest.mark.parametrize(
    "limit_days",
    [
        None,
        0,
        1,
        10,
        99999999999,
        -1,
        -0,
        -999999999999,
    ],
)
def test_reset_limit_days(test_db: SqliteDb, test_user: DbUser, limit_days: int):
    test_db.set_limit_days(user_id=test_user.id, limit_days=limit_days)
    user = test_db.get_user(user_id=test_user.id)
    assert user is not None
    assert user.limit_days == limit_days
    test_db.reset_limit_days(user_id=test_user.id)
    u = test_db.get_user(user_id=test_user.id)
    assert u is not None
    assert u.limit_days is None


def test_is_doctor_in_limit():
    user = DbUser(id=1, limit_days=1)
    doctor = Doctor.model_validate(
        {
            "id": "200",
            "name": "Бибилова Венера Георгиевна",
            "freeParticipantCount": 6,
            "freeTicketCount": 6,
            "lastDate": "2025-11-06T00:00:00",
            "nearestDate": "2025-11-06T00:00:00",
            "ariaNumber": "608",
            "districtId": "8",
            "lpuId": 143,
            "specialtyId": "52",
        }
    )
    check = CheckerApp.is_doc_nearestDate_in_user_limit_days(user=user, doctor=doctor)
    assert check is False

