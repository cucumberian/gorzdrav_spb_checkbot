import pytest
from gorzdrav.endpoint import GorzdravEndpoint
from config import Config


def test_api_url():
    assert GorzdravEndpoint.api_url == Config.API_URL


def test_districts_url():
    assert (
        GorzdravEndpoint.get_districts_endpoint()
        == f"{Config.API_URL}/shared/districts"
    )


def test_lpus_endpoint():
    res = GorzdravEndpoint.get_lpus_endpoint()
    assert res == f"{Config.API_URL}/shared/lpus"
    districtId = "aaa"
    res2 = GorzdravEndpoint.get_lpus_endpoint(districtId=districtId)
    assert res2 == f"{Config.API_URL}/shared/district/{districtId}/lpus"


@pytest.mark.parametrize("lpuId", [(-1,), (1,), (0,)])
def test_get_specialties_url(lpuId: int):
    res = GorzdravEndpoint.get_specialties_endpoint(lpuId=lpuId)
    assert res == f"{Config.API_URL}/schedule/lpu/{lpuId}/specialties"


@pytest.mark.parametrize(
    "lpuId, specialtyId",
    [(1, 1), (1, "1"), (1, "aa"), (9999, 1), (-2, "a")],
)
def test_get_doctors_endpoint(lpuId, specialtyId):
    res = GorzdravEndpoint.get_doctors_endpoint(lpuId, specialtyId)
    assert res == (
        f"{Config.API_URL}/schedule"
        + f"/lpu/{lpuId}"
        + f"/speciality/{specialtyId}/doctors"
    )


@pytest.mark.parametrize("lpuId, doctorId", [(1, "1"), (1, "doctor"), (-1, "")])
def test_get_timetable_endpoint(lpuId: int, doctorId: str):
    res = GorzdravEndpoint.get_timetable_endpoint(lpuId, doctorId)
    assert res == f"{Config.API_URL}/schedule/lpu/{lpuId}/doctor/{doctorId}/timetable"


@pytest.mark.parametrize(
    "lpuId, doctorId",
    [
        (1, "1"),
        (1, "2"),
        (0, "123123"),
        (123141, "dasdqwe"),
    ],
)
def test_get_appointments_endpoint(lpuId: int, doctorId: str):
    res = GorzdravEndpoint.get_appointments_endpoint(lpuId, doctorId)
    assert (
        res == f"{Config.API_URL}/schedule/lpu/{lpuId}/doctor/{doctorId}/appointments"
    )
