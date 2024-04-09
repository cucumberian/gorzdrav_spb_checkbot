import validators  # pip3 install validators
import dns.resolver  # pip3 install dnspython
import re


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


def get_ids_from_gorzdrav_url(url: str) -> dict | None:
    """
    Парсит ссылку на запись к врачу с сайта горздрава спб
    и возвращает идентификаторы
    - идентификатор медицинского учреждения (id)
    - идентификатор специальности врача (str)
    - идентификатор врача (str)
    """
    lpu_regex = r"lpu\%22:\%22(\d+)\%22"
    specialty_regex = r"speciality\%22:\%22(\S+?)\%22"
    doctor_regex = r"doctor\%22:\%22(\S+?)\%22"
    schedule_regex = r"schedule\%22:\%22(\S+?)\%22"

    doctor_search = re.search(doctor_regex, url)
    schedule_search = re.search(schedule_regex, url)
    doctorId = None
    if doctor_search:
        doctorId = str(doctor_search.group(1))
    elif schedule_search:
        doctorId = str(schedule_search.group(1))
    else:
        return None
    try:
        lpuId = int(re.search(lpu_regex, url).group(1))
        specialtyId = str(re.search(specialty_regex, url).group(1))
    except Exception:
        return None
    return {
        "lpuId": lpuId,
        "specialtyId": specialtyId,
        "doctorId": doctorId,
    }
