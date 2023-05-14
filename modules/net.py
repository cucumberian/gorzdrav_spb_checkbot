import re
import requests
import datetime
import time

def get_json_data(url: str) -> dict:
    try:
        response = requests.get(url)
        return response.json()
    except:
        return None
    
class GorzdravSpbAPI:
    _INFO="""
        Апи взято с jquery запросов с сайта gorzdrav.spb.ru
        - https://gorzdrav.spb.ru/_api/api/v2/shared/districts - список районов
        - https://gorzdrav.spb.ru/_api/api/v2/shared/district/10/lpus - список медучереждений в 10 районе
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/229/specialties - информация по всем свободным специальностям в больнице с ид 229
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/speciality/981/doctors - информация по доступным врачам в больнице 30 по специальности 981
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1138/doctor/36/timetable - расписание врача 36 в больнице 1138
        - https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/doctor/222618/appointments - доступные назначения к врачу
    """
    
    def __init__(self):
        self._districts_url = "https://gorzdrav.spb.ru/_api/api/v2/shared/districts"

    def get_hospitals_url(self, district_id: int) -> str:
        return f"https://gorzdrav.spb.ru/_api/api/v2/shared/district/{district_id}/lpus"

    def get_specialities_url(self, hospital_id: int) -> str:
        return f"https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/{hospital_id}/specialties"

    def get_doctors_url(self, hospital_id: int, speciality_id: int) -> str:
        link = f"https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/{hospital_id}/speciality/{speciality_id}/doctors"
        return link

    @property
    def districts_url(self) -> str:
        return self._districts_url
    
    @property
    def districts(self) -> list:
        """
        Список районов города
        """
        response = requests.get(self._districts_url)
        return response.json().get('result')

    def get_hospitals(self, district_id: int) -> list:
        """
        Список всех госпиталей в указанном районе города
        """
        link = self.get_hospitals_url(district_id)
        response = requests.get(link)
        return response.json().get('result')
    
    def get_specialities(self, hospital_id: int) -> list:
        """
        Список всех кабинетов и талонов в мед. учереждении
        """
        link = self.get_specialities_url(hospital_id)
        response = requests.get(link)
        return response.json().get('result')
    
    def get_doctors(self, hospital_id: int, speciality_id: int) -> list:
        """
        Информация по врачам выбранной специальности в мед. учереждении
        """
        link = self.get_doctors_url(
            hospital_id=hospital_id, 
            speciality_id=speciality_id
        )
        response = requests.get(link)
        return response.json().get('result')
    
    def get_doctor(self, hospital_id: int, speciality_id: int, doctor_id: int):
        """
        Получает данные доктора с сайта горздрава и возвращает объект класса Doctor
        """
        doctors = self.get_doctors(
            hospital_id=hospital_id, 
            speciality_id=speciality_id
        )
        if not doctors:
            return None
        
        doctor = [*filter(lambda i: i.get('id') == f"{doctor_id}", doctors)]
        if doctor:
            doctor = doctor[0]
            doctor['hospital_id'] = hospital_id
            doctor['speciality_id'] = speciality_id
        return self.Doctor(doctor) if doctor else None

    def is_gorzdrav(self, url):
        """
        Проверяет ссылку - ведет ли она на сайт горздрава
        """
        regex = r'^https://gorzdrav.spb.ru/service-free-schedule#'
        return bool(re.match(regex, url))

    def get_ids_from_gorzdrav_url(self, url):
        """
        Парсит ссылку на запись к врачу с сайта горздрава спб и возвращает идентификаторы
        - идентификатор медицинского учереждения
        - идентификатор специальности врача
        - идентификатор врача
        """
        hospital_regex = r'lpu\%22:\%22(\d+)%22'
        speciality_regex = r'speciality\%22:\%22(\w+)%22'
        doctor_regex = r'doctor\%22:\%22(\d+)%22'

        try:
            hospital_id = int(re.search(hospital_regex, url).group(1))
            speciality_id = int(re.search(speciality_regex, url).group(1))
            doctor_id = int(re.search(doctor_regex, url).group(1))
        except:
            return None
        
        return {
            'hospital_id': hospital_id,
            'speciality_id': speciality_id,
            'doctor_id': doctor_id,
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

    class Doctor:
        def __init__(self, doctor_info: dict):
            self._info = doctor_info

        def __str__(self):
            return f"врач {self.name}, талонов: {self.freeTicketCount}, мест для записи: {self.freeParticipantCount}"
        
        def __repr__(self):
            return self.__str__()

        @property
        def info(self):
            """
            Возврвщает словарь {'doctor_id', 'speciality_id', 'hospital_id', ...}
            """
            return self._info

        @property
        def id(self):
            return self.info.get('id')

        @property
        def hospital_id(self):
            return self.info.get('hospital_id')
        
        @property
        def speciality_id(self):
            return self.info.get('speciality_id')

        @property
        def name(self):
            return self.info.get('name', "<нет имени>")
        
        @property
        def lastDate(self):
            return datetime.datetime.strptime(self.info.get('lastDate'), '%Y-%m-%d %H:%M')
        
        @property
        def nearestDate(self):
            return datetime.datetime.strptime(self.info.get('nearestDate'), '%Y-%m-%d %H:%M')
        
        @property
        def freeTicketCount(self):
            return self.info.get('freeTicketCount', 0)
        
        @property
        def freeParticipantCount(self):
            return self.info.get('freeParticipantCount', 0)
        
        @property
        def is_free(self):
            return self.freeParticipantCount > 0 or self.freeTicketCount > 0

        @property
        def link(self):
            district_id = self.info.get('districtId') or ''
            return f"https://gorzdrav.spb.ru/service-free-schedule#%5B\
                %7B%22district%22:%22{district_id}%22%7D,\
                %7B%22lpu%22:%22{self.hospital_id}%22%7D,\
                %7B%22speciality%22:%22{self.speciality_id}%22%7D,\
                %7B%22schedule%22:%22{self.id}%22%7D,\
                %7B%22doctor%22:%22{self.id}%22%7D%5D"
        
        def update(self):
            self._info = GorzdravSpbAPI().get_doctor(
                hospital_id = self.hospital_id, 
                speciality_id = self.speciality_id, 
                doctor_id = self.id
            ).info


