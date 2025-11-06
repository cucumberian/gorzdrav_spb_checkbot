import time
from typing import Any

import requests

from config import Config
from gorzdrav import exceptions

from .models import (
    ApiAppointment,
    ApiDistrict,
    ApiDoctor,
    ApiLPU,
    ApiResponse,
    ApiSpecialty,
    ApiTimetable,
    Doctor,
)
from gorzdrav.endpoint import GorzdravEndpoint


class Gorzdrav:
    """
    Класс для обращения к API Gorzdrav.spb.ru
    """

    __headers = Config.HEADERS

    @staticmethod
    def generate_link(
        districtId: str,
        lpuId: int,
        specialtyId: str,
        scheduleId: str,
    ) -> str:
        base_link = "https://gorzdrav.spb.ru/service-free-schedule#"
        addon = f"""%5B%7B%22district%22:%22{districtId}%22%7D,%7B%22lpu%22:%22{lpuId}%22%7D,%7B%22speciality%22:%22{specialtyId}%22%7D,%7B%22schedule%22:%22{scheduleId}%22%7D,%7B%22doctor%22:%22{scheduleId}%22%7D%5D"""
        return base_link + addon

    @classmethod
    def __get_result(cls, url: str, sleep_time: float = 1.0) -> Any:
        """
        Возвращает содержимое поля `result` в json после запроса по url
        Args:
            url: str: url для запроса
            sleep_time: float: задержка перед запросом
        Returns:
            Any: результат
        Raises:
            HttpError: если произошла ошибка запроса
            Exception: если не удалось преобразовать в json
            GorzdravExceptionBase: если `success` в json = False
        """
        if sleep_time > 0.05:
            time.sleep(sleep_time)
        response = requests.get(url, headers=cls.__headers)
        response.raise_for_status()
        response_json = response.json()
        api_response: ApiResponse = ApiResponse(**response_json)
        if not api_response.success:
            response_message = api_response.message or "Неизвестное сообщение об ошибке"
            raise exceptions.GorzdravException(
                message=response_message,
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
        Список районов города
        """
        url = GorzdravEndpoint.get_districts_endpoint()
        result = cls.__get_result(url)
        districts = cls.__parse_list_in_result(result, ApiDistrict)
        return districts

    @classmethod
    def get_lpus(cls, districtId: str | None = None) -> list[ApiLPU]:
        """
        Список медучреждений.
        Если ид района не указан то получаем медучреждения во всех районах
        """
        url = GorzdravEndpoint.get_lpus_endpoint(districtId)
        result = cls.__get_result(url)
        lpus = cls.__parse_list_in_result(result, ApiLPU)
        return lpus

    @classmethod
    def get_lpu(cls, lpuId: int) -> ApiLPU:
        """
        Информация о медучреждении
        Args:
            lpuId: int: id медучреждения
        Returns:
            ApiLPU: информация о медучреждении
        """
        url = GorzdravEndpoint.get_lpu_endpoint(lpuId=lpuId)
        result = cls.__get_result(url=url)
        lpu = ApiLPU(**result)
        return lpu

    @classmethod
    def get_specialties(cls, lpuId: int) -> list[ApiSpecialty]:
        """
        Список всех специальностей в медучреждении
        Args:
            lpuId: int: id медучреждения
        Returns:
            list[ApiSpecialty]: список специальностей
        """
        url = GorzdravEndpoint.get_specialties_endpoint(lpuId=lpuId)
        try:
            result = cls.__get_result(url)
        except exceptions.NoSpecialtiesException:
            return []
        specialties = cls.__parse_list_in_result(result, ApiSpecialty)
        return specialties

    @classmethod
    def get_doctors(cls, lpuId: int, specialtyId: str) -> list[ApiDoctor]:
        """
        Список врачей в медучреждении по специальности
        Args:
            lpuId: int: id медучреждения по горздраву
            specialtyId: str: id специальности по горздраву
        Returns:
            list[ApiDoctor]: список врачей
        """
        url = GorzdravEndpoint.get_doctors_endpoint(
            lpuId=lpuId, specialtyId=specialtyId
        )
        try:
            result = cls.__get_result(url)
        except exceptions.NoDoctorsException:
            return []
        doctors = cls.__parse_list_in_result(result, ApiDoctor)
        return doctors

    @classmethod
    def get_doctor(
        cls,
        lpuId: int,
        specialtyId: str,
        doctorId: str,
        districtId: str | None = None,
    ) -> Doctor | None:
        """
        Возвращает доктора по его параметрам
        Args:
            lpuId: int: id медучреждения по горздраву
            specialtyId: str: id специальности по горздраву
            doctorId: str: id врача
            districtId: str | None: id района
        Returns:
            Doctor | None: врач если найден
        """
        doctors: list[ApiDoctor] = cls.get_doctors(lpuId, specialtyId)
        for doctor in doctors:
            if doctor.id == doctorId:
                doc = Doctor(
                    **doctor.model_dump(),
                    districtId=districtId,
                    lpuId=lpuId,
                    specialtyId=specialtyId,
                )

                return doc
        return None

    @classmethod
    def get_timetables(cls, lpu_id: int, doctor_id: str) -> list[ApiTimetable]:
        """
        Возвращает список расписаний врача из медучреждения с gorzdrav.spb.ru.
        Args:
            lpu_id: int: ид медучреждения
            doctor_id: str: id врача.
        Returns:
            list[ApiTimetable]: список расписаний.
        """
        url = GorzdravEndpoint.get_timetable_endpoint(lpuId=lpu_id, doctorId=doctor_id)
        result = cls.__get_result(url)
        timetables: list[ApiTimetable] = cls.__parse_list_in_result(
            objects=result, model=ApiTimetable
        )
        return timetables

    @classmethod
    def get_appointments(
        cls,
        lpu_id: int,
        doctor_id: str,
    ) -> list[ApiAppointment]:
        url = GorzdravEndpoint.get_appointments_endpoint(
            lpuId=lpu_id, doctorId=doctor_id
        )
        try:
            result = cls.__get_result(url)
        except exceptions.NoTicketsException:
            return []
        appointments: list[ApiAppointment] = cls.__parse_list_in_result(
            objects=result, model=ApiAppointment
        )
        return appointments
