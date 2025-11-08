import re
import json
from urllib.parse import unquote
from pydantic_core import ValidationError

import validators  # pip3 install validators
import dns.resolver  # pip3 install dnspython
from .models import LinkParsingResult


def is_domain(text):
    return bool(validators.domain(text))


def is_ipv4(text):
    return bool(validators.ip_address.ipv4(text))


def is_url(text):
    return bool(validators.url(text))


def is_valid_dns(text):
    try:
        dns_resolved = dns.resolver.query(text, "A")
    except Exception:
        dns_resolved = None
    return bool(dns_resolved)


def is_gorzdrav(url: str) -> bool:
    """
    Проверяет ссылку - ведет ли она на сайт горздрава
    """
    regex = r"^https://gorzdrav.spb.ru/service-free-schedule#"
    return bool(re.match(regex, url))


def get_ids_from_gorzdrav_url(url: str) -> LinkParsingResult | None:
    """
    Парсит ссылку на запись к врачу с сайта горздрава спб
    и возвращает идентификаторы
    - идентификатор медицинского учреждения (id)
    - идентификатор специальности врача (str)
    - идентификатор врача (str)
    Args:
        url: str - ссылка на запись к врачу с сайта горздрава спб
    Returns:
        LinkParsingResult | None - результат парсинга ссылки
    """
    lpu_regex = r"lpu\%22:\%22(\d+)\%22"
    specialty_regex = r"speciality\%22:\%22(\S+?)\%22"
    doctor_regex = r"doctor\%22:\%22(\S+?)\%22"
    schedule_regex = r"schedule\%22:\%22(\S+?)\%22"
    district_regex = r"district\%22:\%22(\S+?)\%22"

    doctor_search = re.search(doctor_regex, url)
    schedule_search = re.search(schedule_regex, url)
    doctorId = None
    if doctor_search:
        doctorId: str = unquote(doctor_search.group(1))
    elif schedule_search:
        doctorId: str = unquote(schedule_search.group(1))
    else:
        return None
    try:
        lpuId: int = int(re.search(lpu_regex, url).group(1))
        specialtyId: str = unquote(re.search(specialty_regex, url).group(1))
        districtId: str = unquote(re.search(district_regex, url).group(1))
    except Exception:
        return None
    try:
        return LinkParsingResult(
            lpuId=lpuId,
            specialtyId=specialtyId,
            doctorId=doctorId,
            districtId=districtId,
        )
    except ValidationError:
        return None


def parse_url(url: str) -> LinkParsingResult | None:
    """
    Парсит строку от горздрава на предмет идишников
    Строка декодируется после процентного кодирования
    и часть и идишками преобразуется в json, который
    затем собирается в словарь.
    Args:
        url (str): ссылка для извлечения района, лпу, специальности и врача.
    Returns:
        LinkParsingResult: готовый объект с извлечёнными параметрами.
    """
    try:
        unquoted_url = unquote(string=url, encoding="utf-8")
        free_schedule_regex = r"https://gorzdrav.spb.ru/service-free-schedule#(.+)"
        url_substring = re.search(free_schedule_regex, unquoted_url).group(1)
        json_result = json.loads(url_substring)
        json_dict = {}
        [json_dict.update(d) for d in json_result]
        return LinkParsingResult(
            districtId=json_dict.get("district"),
            lpuId=json_dict["lpu"],
            specialtyId=json_dict["speciality"],
            doctorId=json_dict["doctor"],
        )
    except Exception:
        return None
