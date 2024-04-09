import time
import requests
import re
from typing import Any
from exceptions import api_exceptions
from models.pydantic_models import ApiDistrict
from models.pydantic_models import ApiLPU
from models.pydantic_models import ApiSpecialty
from models.pydantic_models import ApiDoctor
from models.pydantic_models import ApiTimetable
from models.pydantic_models import ApiAppointment
from models.pydantic_models import ApiResponse
from pprint import pprint
from config import Config


class Gorzdrav:
    __gorzdrav_api_base_url = Config.api_url
    __shared_url = f"{__gorzdrav_api_base_url}/shared"
    __schedule_url = f"{__gorzdrav_api_base_url}/schedule"
    __headers = Config.headers or None


    @classmethod
    def __get_district_endpoint(cls) -> str:
        """
        Get endpoint for getting all districts from gorzdrav.spb.ru
        Returns:
            str: endpoint for getting all districts.
        """
        return f"{cls.__shared_url}/districts"

    @classmethod
    def __get_lpu_endpoint(cls, district_id: str) -> str:
        """
        Get endpoint for getting all lpus from gorzdrav.spb.ru
        Args:
            district_id: str: id of district.
        Returns:
            str: endpoint for getting all lpus.
        """
        return f"{cls.__shared_url}/district/{district_id}/lpus"

    @classmethod
    def __get_specialties_endpoint(cls, lpu_id: int) -> list[ApiSpecialty]:
        """
        Get endpoint for getting all specialties from gorzdrav.spb.ru
        Args:
            lpu_id: int: id of lpu.
        Returns:
            str: endpoint for getting all specialties.
        """
        return f"{cls.__schedule_url}/lpu/{lpu_id}/specialties"

    @classmethod
    def __get_doctors_endpoint(cls, lpu_id: int, specialty_id: str) -> str:
        """
        Get endpoint for getting all doctors from gorzdrav.spb.ru
        Args:
            lpu_id: int: id of lpu.
            specialty_id: str: id of specialty.
        Returns:
            str: endpoint for getting all doctors.
        """
        return f"{cls.__schedule_url}/lpu/{lpu_id}/speciality/{specialty_id}/doctors"

    @classmethod
    def __get_timetable_endpoint(cls, lpu_id: int, doctor_id: str) -> str:
        """
        Get endpoint for getting timetable from gorzdrav.spb.ru
        Args:
            lpu_id: int: id of lpu.
            doctor_id: str: id of doctor.
        Returns:
            str: endpoint for getting timetable.
        """
        return (
            f"{cls.__schedule_url}/lpu/{lpu_id}/doctor/{doctor_id}/timetable"
        )

    @classmethod
    def __get_appointments_endpoint(cls, lpu_id: int, doctor_id: str) -> str:
        """
        Get endpoint for getting appointments from gorzdrav.spb.ru
        Args:
            lpu_id: int: id of lpu.
            doctor_id: str: id of doctor.
        Returns:
            str: endpoint for getting appointments.
        """
        return f"{cls.__schedule_url}/lpu/{lpu_id}/doctor/{doctor_id}/appointments"

    @classmethod
    def __get_result(cls, url: str, sleep_time: float = 1.0) -> Any:
        """
        Get result from response.json from url
        Args:
            url: str: url for request.
        Returns:
            Any: result of request.
        Raises:
            HttpError: if request failed.
            Exception: if request failed in json.
            GorzdravExceptionBase: if json success status is False.
        """
        if sleep_time > 0.05:
            time.sleep(sleep_time)
        response = requests.get(url, headers=cls.__headers)
        response.raise_for_status()
        response_json = response.json()
        pprint(response_json)
        api_response: ApiResponse = ApiResponse(**response_json)
        if not api_response.success:
            raise api_exceptions.GorzdravException(
                message=api_response.message,
                errorCode=api_response.errorCode,
                url=url,
            )
        return api_response.result

    @staticmethod
    def __parse_list_in_result(objects: list[Any], model: Any) -> list[Any]:
        objects = [model(**result) for result in objects]
        return objects

    @classmethod
    def get_districts(cls) -> list[ApiDistrict]:
        """
        Get all districts from gorzdrav.spb.ru.
        Returns:
            list[ApiDistrict]: list of districts.
            Raises:
            Exception: if request failed.
        """

        districts = cls.__get_result(cls.__get_district_endpoint())
        return cls.__parse_list_in_result(districts, ApiDistrict)

    @classmethod
    def get_lpus(cls, district_id: str) -> list[ApiLPU]:
        """
        Get all lpus from gorzdrav.spb.ru.
        Args:
            district_id: id of district.
        Returns:
            list[ApiLPU]: list of lpus.
            Raises:
            Exception: if request failed.
        """
        url = cls.__get_lpu_endpoint(district_id)
        result = cls.__get_result(url)
        return cls.__parse_list_in_result(objects=result, model=ApiLPU)

    @classmethod
    def get_specialties(cls, lpu_id: int) -> list[ApiSpecialty]:
        """
        Get all specialties from gorzdrav.spb.ru.
        Args:
            lpu_id: int: id of lpu.
        Returns:
            list[ApiSpecialty]: list of specialties.
            Raises:
            Exception: if request failed.
        """
        url = cls.__get_specialties_endpoint(lpu_id=lpu_id)
        try:
            result = cls.__get_result(url)
        except api_exceptions.NoSpecialtiesException:
            return []
        specialties: list[ApiSpecialty] = cls.__parse_list_in_result(
            objects=result, model=ApiSpecialty
        )
        return specialties

    @classmethod
    def get_doctors(cls, lpu_id: int, specialty_id: str) -> list[ApiDoctor]:
        """
        Get all doctors from gorzdrav.spb.ru.
        Args:
            lpu_id: int: id of lpu.
            specialty_id: str: id of specialty.
        Returns:
            list[ApiDoctor]: list of doctors.
            Raises:
            Exception: if request failed.
        {
            "success": false,
            "errorCode": 38,
            "message": "Отсутствуют специалисты для приёма по выбранной специальности. Обратитесь в регистратуру медорганизации",
            "requestId": "c29d3cd4-88cd-4d97-acce-aefd98d5264b"
        }
        """
        url = cls.__get_doctors_endpoint(
            lpu_id=lpu_id, specialty_id=specialty_id
        )
        try:
            result = cls.__get_result(url)
        except api_exceptions.NoDoctorsException:
            return []
        doctors: list[ApiDoctor] = cls.__parse_list_in_result(
            objects=result, model=ApiDoctor
        )
        return doctors

    @classmethod
    def get_doctor(
        cls, lpuId: int, specialtyId: str, doctorId: str
    ) -> ApiDoctor | None:
        """
        Get doctor from gorzdrav.spb.ru.
        Args:
            lpu_id: int: id of lpu.
            specialty_id: str: id of specialty.
            doctor_id: str: id of doctor.
        Returns:
            ApiDoctor: doctor.
            Raises:
            Exception: if request failed.
        """
        doctors = cls.get_doctors(lpu_id=lpuId, specialty_id=specialtyId)
        for doctor in doctors:
            if doctor.id == doctorId:
                return doctor
        return None
