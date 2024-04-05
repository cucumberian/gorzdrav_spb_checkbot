import pytest
from modules.net import GorzdravSpbAPI
from config import Config


def test_api_url():
    assert GorzdravSpbAPI.api_url == Config.api_url


def test_hospitals_url():
    res = GorzdravSpbAPI.hospitals_url
    assert res == f"{Config.api_url}/shared/lpus"


@pytest.mark.parametrize("hospital_id", [(1,), ("1",), ("aa",)])
def test_get_specialties_url(hospital_id: str | int):
    res = GorzdravSpbAPI.get_specialties_url(hospital_id)
    assert res == f"{Config.api_url}/schedule/lpu/{hospital_id}/specialties"


@pytest.mark.parametrize(
    "hospital_id, speciality_id",
    [(1, 1), (1, "1"), (1, "aa"), ("1", 1), ("aa", "a")],
)
def test_get_doctors_url(hospital_id, speciality_id):
    res = GorzdravSpbAPI.get_doctors_url(hospital_id, speciality_id)
    assert res == (
        f"{Config.api_url}/schedule"
        + f"/lpu/{hospital_id}"
        + f"/speciality/{speciality_id}/doctors"
    )
