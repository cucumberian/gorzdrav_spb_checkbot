import re
import requests
import datetime
import time

from config import Config
from . import models


def get_json_data(url: str) -> dict:
    try:
        response = requests.get(url)
        return response.json()
    except:
        return None


class GorzdravSpbAPI:
    _INFO = """
        Апи взято с jquery запросов с сайта gorzdrav.spb.ru
        - https://gorzdrav.spb.ru/_api/api/v2/shared/districts - список районов
        - https://gorzdrav.spb.ru/_api/api/v2/shared/lpus - список медучреждений во всех районах
        - https://gorzdrav.spb.ru/_api/api/v2/shared/district/10/lpus - список медучереждений в 10 районе
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/229/specialties - информация по всем свободным специальностям в больнице с ид 229
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/speciality/981/doctors - информация по доступным врачам в больнице 30 по специальности 981
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1138/doctor/36/timetable - расписание врача 36 в больнице 1138
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/doctor/222618/appointments - доступные назначения к врачу
    """
    api_url = Config.api_url
    districts_url = Config.api_url + "/shared/districts"
    hospitals_url = Config.api_url + "/shared/lpus"

    def __init__(self):
        pass

    @staticmethod
    def get_specialties_url(hospital_id: int | str) -> str:
        return f"{Config.api_url}/schedule/lpu/{hospital_id}/specialties"

    @staticmethod
    def get_doctors_url(
        hospital_id: int | str, speciality_id: int | str
    ) -> str:
        link = (
            Config.api_url
            + "/"
            + f"schedule/lpu/{hospital_id}"
            + "/"
            + f"speciality/{speciality_id}/doctors"
        )
        return link

    @property
    def districts(self) -> list[models.ApiDistrict]:
        """
        Список районов города
        """
        response = requests.get(self.districts_url, headers=Config.headers)
        if not response.ok:
            raise Exception(response.text)
        result = response.json().get("result")
        districts = [models.ApiDistrict(**d) for d in result]
        return districts

    @property
    def hospitals(self) -> list[models.ApiHospital]:
        """Список всех госпиталей"""
        response = requests.get(
            self.__class__.hospitals_url, headers=Config.headers
        )
        if not response.ok:
            raise Exception(response.text)
        json = response.json()
        hospitals = [models.ApiHospital(**h) for h in json.get("result")]
        return hospitals

    def get_specialties(self, hospital_id: int) -> list[models.ApiSpeciality]:
        """
        Список всех кабинетов и талонов в мед. учреждении
        """
        link = self.get_specialties_url(hospital_id)
        response = requests.get(link, headers=Config.headers)
        if not response.ok:
            raise Exception(response.text)
        json = response.json()
        specialties = [models.ApiSpeciality(**s) for s in json.get("result")]
        return specialties

    def get_doctors(
        self, hospital_id: int | str, speciality_id: int | str
    ) -> list[models.ApiDoctor]:
        """
        Информация по врачам выбранной специальности в мед. учреждении
        """
        link = self.get_doctors_url(
            hospital_id=hospital_id, speciality_id=speciality_id
        )
        response = requests.get(link, headers=Config.headers)
        if not response.ok:
            raise Exception(response.text)
        result = response.json().get("result")
        doctors = [models.ApiDoctor(**d) for d in result]
        return doctors

    def get_doctor(
        self, hospital_id: int | str, speciality_id: str | int, doctor_id: str
    ) -> models.Doctor | None:
        """
        Получает данные доктора с сайта горздрава
        и возвращает объект класса models.Doctor
        params: hospital_id: ид медучреждения
        type: hospital_id: int | str
        params: speciality_id: ид специальности врача
        type: speciality_id: str | int
        params: doctor_id: ид врача
        type: doctor_id: str
        return: Doctor | None
        """
        doctors: list[models.Doctor] = self.get_doctors(
            hospital_id=hospital_id, speciality_id=speciality_id
        )
        if not doctors:
            return None
        filtered_doctors = [
            *filter(lambda d: str(d.id) == str(doctor_id), doctors)
        ]
        if not filtered_doctors:
            return None
        doctor = filtered_doctors[0]
        return models.Doctor(
            id=doctor.id, hospital_id=hospital_id, speciality_id=speciality_id
        )

    def is_gorzdrav(self, url):
        """
        Проверяет ссылку - ведет ли она на сайт горздрава
        """
        regex = r"^https://gorzdrav.spb.ru/service-free-schedule#"
        return bool(re.match(regex, url))

    def get_ids_from_gorzdrav_url(self, url):
        """
        Парсит ссылку на запись к врачу с сайта горздрава спб
        и возвращает идентификаторы
        - идентификатор медицинского учереждения
        - идентификатор специальности врача
        - идентификатор врача
        """
        hospital_regex = r"lpu\%22:\%22(\d+)%22"
        speciality_regex = r"speciality\%22:\%22(\w+)%22"
        doctor_regex = r"doctor\%22:\%22(\d+)%22"

        try:
            hospital_id = int(re.search(hospital_regex, url).group(1))
            speciality_id = int(re.search(speciality_regex, url).group(1))
            doctor_id = int(re.search(doctor_regex, url).group(1))
        except:
            return None

        return {
            "hospital_id": hospital_id,
            "speciality_id": speciality_id,
            "doctor_id": doctor_id,
        }

    def url_parse(self, url: str):
        """
        Парсинг ссылки со врачом
        Возвращается словарь {'hospital_id', 'speciality_id', 'doctor_id'}
        """
        if self.is_gorzdrav(url):
            return self.get_ids_from_gorzdrav_url(url)
        else:
            return None

