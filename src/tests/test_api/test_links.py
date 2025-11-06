import pytest

from gorzdrav import validate
from gorzdrav.api import Gorzdrav


def test_parsing():
    link = "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%2214%22%7D,%7B%22lpu%22:%22308%22%7D,%7B%22speciality%22:%2240%22%7D,%7B%22schedule%22:%22127%22%7D%5D"
    parsing_result = validate.get_ids_from_gorzdrav_url(url=link)
    assert parsing_result is not None
    assert parsing_result.districtId == "14"


@pytest.mark.parametrize(
    "districtId, lpuId, specialtyId, scheduleId, expected_link",
    [
        (
            "17",
            260,
            "4",
            "186",
            "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%2217%22%7D,%7B%22lpu%22:%22260%22%7D,%7B%22speciality%22:%224%22%7D,%7B%22schedule%22:%22186%22%7D,%7B%22doctor%22:%22186%22%7D%5D",
        )
    ],
)
def test_link(
    districtId: str,
    lpuId: int,
    specialtyId: str,
    scheduleId: str,
    expected_link: str,
):
    doctor_link = Gorzdrav.generate_link(
        districtId=districtId,
        lpuId=lpuId,
        specialtyId=specialtyId,
        scheduleId=scheduleId,
    )
    assert doctor_link == expected_link
    parsing_result = validate.get_ids_from_gorzdrav_url(url=doctor_link)
    assert parsing_result is not None
    assert parsing_result.districtId == districtId
    assert parsing_result.lpuId == lpuId
    assert parsing_result.specialtyId == specialtyId
    assert parsing_result.doctorId == scheduleId
