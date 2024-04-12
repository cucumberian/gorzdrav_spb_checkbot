import pytest
from gorzdrav.api import Gorzdrav
from config import Config


def test_api_url():
    assert Gorzdrav._Gorzdrav__api_url == Config.api_url


def test_districts_url():
    assert (
        Gorzdrav._Gorzdrav__get_districts_endpoint()
        == f"{Config.api_url}/shared/districts"
    )


def test_lpus_endpoint():
    res = Gorzdrav._Gorzdrav__get_lpus_endpoint()
    assert res == f"{Config.api_url}/shared/lpus"
    districtId = "aaa"
    res2 = Gorzdrav._Gorzdrav__get_lpus_endpoint(districtId=districtId)
    assert res2 == f"{Config.api_url}/shared/district/{districtId}/lpus"


@pytest.mark.parametrize("lpuId", [(".da",), ("1",), ("aa",)])
def test_get_specialties_url(lpuId: str):
    res = Gorzdrav._Gorzdrav__get_specialties_endpoint(lpuId)
    assert res == f"{Config.api_url}/schedule/lpu/{lpuId}/specialties"


@pytest.mark.parametrize(
    "lpuId, specialtyId",
    [(1, 1), (1, "1"), (1, "aa"), (9999, 1), (-2, "a")],
)
def test_get_doctors_endpoint(lpuId, specialtyId):
    res = Gorzdrav._Gorzdrav__get_doctors_endpoint(lpuId, specialtyId)
    assert res == (
        f"{Config.api_url}/schedule"
        + f"/lpu/{lpuId}"
        + f"/speciality/{specialtyId}/doctors"
    )


@pytest.mark.parametrize(
    "lpuId, doctorId", [(1, "1"), (1, "doctor"), (-1, "")]
)
def test_get_timetable_endpoint(lpuId: int, doctorId: str):
    res = Gorzdrav._Gorzdrav__get_timetable_endpoint(lpuId, doctorId)
    assert (
        res
        == f"{Config.api_url}/schedule/lpu/{lpuId}/doctor/{doctorId}/timetable"
    )


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
    res = Gorzdrav._Gorzdrav__get_appointments_endpoint(lpuId, doctorId)
    assert (
        res
        == f"{Config.api_url}/schedule/lpu/{lpuId}/doctor/{doctorId}/appointments"
    )
