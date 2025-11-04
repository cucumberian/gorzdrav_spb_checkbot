import datetime
from gorzdrav.models import Doctor
from models.pydantic_models import DbUser
import logging

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
