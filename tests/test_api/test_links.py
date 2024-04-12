import pytest
from gorzdrav import validate
from gorzdrav.api import Gorzdrav


@pytest.mark.parametrize(
    "link, districtId, lpuId, specialtyId, doctorId",
    [
        (
            "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%2214%22%7D,%7B%22lpu%22:%22308%22%7D,%7B%22speciality%22:%2240%22%7D,%7B%22schedule%22:%22127%22%7D%5D",
            "14",
            308,
            "40",
            "127",
        ),
        (
            "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%223%22%7D,%7B%22lpu%22:%22191%22%7D,%7B%22speciality%22:%2259%22%7D,%7B%22doctor%22:%22%D0%BF99.553%22%7D%5D",
            "3",
            191,
            "59",
            "п99.553",
        ),
        (
            "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%2215%22%7D,%7B%22lpu%22:%22132%22%7D,%7B%22speciality%22:%228%22%7D,%7B%22schedule%22:%221135%22%7D%5D",
            "15",
            132,
            "8",
            "1135",
        ),
        (
            "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%2215%22%7D,%7B%22lpu%22:%22207%22%7D,%7B%22speciality%22:%224%22%7D,%7B%22schedule%22:%22%D0%BF49.106%22%7D%5D",
            "15",
            207,
            "4",
            "п49.106",
        ),
    ],
)
def test_link_parsing(
    link: str, districtId: str, lpuId: int, specialtyId: str, doctorId: str
):
    parsing_result = validate.get_ids_from_gorzdrav_url(url=link)
    assert parsing_result.districtId == districtId
    assert parsing_result.lpuId == lpuId
    assert parsing_result.specialtyId == specialtyId
    assert parsing_result.doctorId == doctorId


def test_parsing():
    link = "https://gorzdrav.spb.ru/service-free-schedule#%5B%7B%22district%22:%2214%22%7D,%7B%22lpu%22:%22308%22%7D,%7B%22speciality%22:%2240%22%7D,%7B%22schedule%22:%22127%22%7D%5D"
    parsing_result = validate.get_ids_from_gorzdrav_url(url=link)
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
    assert parsing_result.districtId == districtId
    assert parsing_result.lpuId == lpuId
    assert parsing_result.specialtyId == specialtyId
    assert parsing_result.doctorId == scheduleId
