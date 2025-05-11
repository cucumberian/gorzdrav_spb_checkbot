import requests
import time
from typing import Any

from config import Config
from .models import ApiResponse
from .models import ApiDistrict
from .models import ApiLPU
from .models import ApiSpecialty
from .models import ApiDoctor
from .models import ApiAppointment
from .models import ApiTimetable
from .models import Doctor
from gorzdrav import exceptions


class Gorzdrav:
    """
    Класс для обращения к API Gorzdrav.spb.ru
    """

    __api_url = Config.API_URL
    __shared_url = f"{__api_url}/shared"
    __schedule_url = f"{__api_url}/schedule"
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
    def __get_districts_endpoint(cls) -> str:
        """
        Маршрут для получения списка районов с gorzdrav.spb.ru
        Returns:
            str: эндпоинт для получения списка районов
        """
        return f"{cls.__shared_url}/districts"

    @classmethod
    def __get_lpus_endpoint(cls, districtId: str | None = None) -> str:
        """
        Маршрут для получения списка медучреждений в районе.
        Если ид района не указан то отдается путь для получения списка всех медучреждений
        Args:
            districtId: str | None: id района
        Returns:
            str: эндпоинт для получения списка медучреждений
        """
        if districtId is None:
            return f"{cls.__shared_url}/lpus"
        return f"{cls.__shared_url}/district/{districtId}/lpus"

    @classmethod
    def __get_lpu_endpoint(cls, lpuId: int) -> str:
        """
        Маршрут для получения информации о медучреждении
        Args:
            lpuId: int: id медучреждения
        Returns:
            ApiLPU: информация о медучреждении
        """
        return f"{cls.__shared_url}/lpu/{lpuId}"

    @classmethod
    def __get_specialties_endpoint(cls, lpuId: int) -> str:
        """
        Маршрут для получения списка специальностей в медучреждении
        Args:
            lpuId: int: id медучреждения
        Returns:
            str: эндпоинт для получения списка специальностей
        """
        return f"{cls.__schedule_url}/lpu/{lpuId}/specialties"

    @classmethod
    def __get_doctors_endpoint(cls, lpuId: int, specialtyId: str) -> str:
        """
        Маршрут для получения списка врачей в медучреждении
        Args:
            lpuId: int: id медучреждения
            specialtyId: str: id специальности
        Returns:
            str: эндпоинт для получения врачей по специальности в поликлинике
        """
        return (
            f"{cls.__schedule_url}"
            + f"/lpu/{lpuId}"
            + f"/speciality/{specialtyId}"
            + "/doctors"
        )

    @classmethod
    def __get_timetable_endpoint(cls, lpuId: int, doctorId: str) -> str:
        """
        Маршрут для получения расписания врача
        Args:
            lpuId: int: id медучреждения
            doctorId: str: id врача
        Returns:
            str: эндпоинт для получения расписания врача
        """
        return f"{cls.__schedule_url}/lpu/{lpuId}/doctor/{doctorId}/timetable"

    @classmethod
    def __get_appointments_endpoint(cls, lpuId: int, doctorId: str) -> str:
        """
        Маршрут для получения доступных назначений к врачу
        Args:
            lpuId: int: id медучреждения
            doctorId: str: id врача
        Returns:
            str: эндпоинт для получения доступных назначений к врачу
        """
        return f"{cls.__schedule_url}/lpu/{lpuId}/doctor/{doctorId}/appointments"

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
            raise exceptions.GorzdravException(
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
        Список районов города
        """
        url = cls.__get_districts_endpoint()
        result = cls.__get_result(url)
        districts = cls.__parse_list_in_result(result, ApiDistrict)
        return districts

    @classmethod
    def get_lpus(cls, districtId: str | None = None) -> list[ApiLPU]:
        """
        Список медучреждений.
        Если ид района не указан то получаем медучреждения во всех районах
        """
        url = cls.__get_lpus_endpoint(districtId)
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
        url = cls.__get_lpu_endpoint(lpuId=lpuId)
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
        url = cls.__get_specialties_endpoint(lpuId=lpuId)
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
        url = cls.__get_doctors_endpoint(lpuId=lpuId, specialtyId=specialtyId)
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
        url = cls.__get_timetable_endpoint(lpu_id=lpu_id, doctor_id=doctor_id)
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
        url = cls.__get_appointments_endpoint(lpu_id=lpu_id, doctor_id=doctor_id)
        try:
            result = cls.__get_result(url)
        except exceptions.NoTicketsException:
            return []
        appointments: list[ApiAppointment] = cls.__parse_list_in_result(
            objects=result, model=ApiAppointment
        )
        return appointments
