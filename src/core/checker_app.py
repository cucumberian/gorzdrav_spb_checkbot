import datetime
import logging

import requests

from gorzdrav.models import ApiAppointment, Doctor
from models.pydantic_models import DbUser
from telegram.types import TGParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CheckerApp:
    @staticmethod
    def is_doc_nearestDate_in_user_limit_days(user: DbUser, doctor: Doctor) -> bool:
        """Проверяет, попадает ли ближайшая дата записи врача в лимит дней пользователя от текущей даты"""
        user_limit_days: int | None = user.limit_days
        # если лимит дней не задан или 0, то врач попадает в лимит дней
        if not user_limit_days:
            return True
        # если лимит отрицательный, то считаем что его нет
        if user_limit_days < 0:
            return True
        # не ищем дальше 99 дней
        if user_limit_days > 99:
            user_limit_days = 99

        # ТУТ НАДО ПОЛУЧАТЬ APPOINTMENTS ВРАЧА И ИСКАТЬ БЛИЖАЙШУЮ ДАТУ
        # https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/{lpu_id}/doctor/{doc_id}/appointments

        # nearest_date - то ближайшее время кода врач на работе (наверное),
        # а не время ближайшего свободного его приёма
        nearest_date: datetime.datetime | None = doctor.nearestDate
        logger.debug("nearest_date: %s", nearest_date)
        if nearest_date is None:
            return False
        # берем тз СПб +3 часа к UTC
        current_date = datetime.datetime.now(
            datetime.timezone(offset=datetime.timedelta(hours=3))
        ).date()

        # 1 день - это сегодня
        # 2 дня - это сегодня и завтра
        delta_days: int = (nearest_date.date() - current_date).days + 1
        logger.debug("delta_days: %s", delta_days)
        return delta_days <= user_limit_days

    # send message to telegram with requests.post
    @staticmethod
    def send_tg_message(
        message: str,
        api_token: str,
        chat_id: int | str,
        parse_mode: TGParseMode | None = None,
    ) -> None:
        """
        Отправка сообщений в телеграм пользователю через requests.post
        :param message: str - сообщение
        :param api_token: str - токен бота
        :param chat_id: - id чата
        :return: None
        """
        url: str = f"https://api.telegram.org/bot{api_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }
        response = requests.post(
            url=url,
            data=data,
            params={"parse_mode": parse_mode},
        )
        if not response.ok:
            print(f"Failed to send message to {chat_id}", response.text)

    @staticmethod
    def check_appointments_in_user_limit_days(
        appointments: list[ApiAppointment],
        user: DbUser,
    ) -> bool:
        """Проверяет есть ли назначения врача в пределах лимита дней пользователя"""
        if not appointments:
            return False

        if not user.limit_days:
            return True
        """True, если есть назначение в переделах установленного лимита у пользователя"""
        current_date = datetime.datetime.now(
            datetime.timezone(offset=datetime.timedelta(hours=3))
        ).date()
        appointments_dates = [
            appointment.visitStart.date() for appointment in appointments
        ]
        print("appointments dates:", appointments_dates)
        appointments_deltas: list[int] = [
            ((i - current_date).days + 1)
            for i in appointments_dates
            if i >= current_date
        ]
        print("appointments deltas:", appointments_deltas)
        is_lower: list[bool] = [i <= user.limit_days for i in appointments_deltas]
        print("is lower:", is_lower)
        return any(is_lower)
