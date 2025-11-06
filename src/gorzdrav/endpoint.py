from config import Config


class GorzdravEndpoint:
    """Класс лоя конструирования эндпоинтов для горздрава"""

    api_url = Config.API_URL
    __shared_url = f"{api_url}/shared"
    __schedule_url = f"{api_url}/schedule"

    @classmethod
    def get_districts_endpoint(cls) -> str:
        """
        Маршрут для получения списка районов с gorzdrav.spb.ru
        Returns:
            str: эндпоинт для получения списка районов
        """
        return f"{cls.__shared_url}/districts"

    @classmethod
    def get_lpus_endpoint(cls, districtId: str | None = None) -> str:
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
    def get_lpu_endpoint(cls, lpuId: int) -> str:
        """
        Маршрут для получения информации о медучреждении
        Args:
            lpuId: int: id медучреждения
        Returns:
            ApiLPU: информация о медучреждении
        """
        return f"{cls.__shared_url}/lpu/{lpuId}"

    @classmethod
    def get_specialties_endpoint(cls, lpuId: int) -> str:
        """
        Маршрут для получения списка специальностей в медучреждении
        Args:
            lpuId: int: id медучреждения
        Returns:
            str: эндпоинт для получения списка специальностей
        """
        return f"{cls.__schedule_url}/lpu/{lpuId}/specialties"

    @classmethod
    def get_doctors_endpoint(cls, lpuId: int, specialtyId: str) -> str:
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
    def get_timetable_endpoint(cls, lpuId: int, doctorId: str) -> str:
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
    def get_appointments_endpoint(cls, lpuId: int, doctorId: str) -> str:
        """
        Маршрут для получения доступных назначений к врачу
        Args:
            lpuId: int: id медучреждения
            doctorId: str: id врача
        Returns:
            str: эндпоинт для получения доступных назначений к врачу
        """
        return f"{cls.__schedule_url}/lpu/{lpuId}/doctor/{doctorId}/appointments"
