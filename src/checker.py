import logging
import time


from config import Config
from core.checker_app import CheckerApp
from depends import sqlite_db as DB
from gorzdrav.api import Gorzdrav
from gorzdrav.models import ApiAppointment, Doctor
from queries.orm import SyncOrm
from telegram.message_composer import TgMessageComposer
from telegram.types import TGParseMode

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

SyncOrm.create_tables()


def old_scheduler(timeout_secs: int):
    # бесконечный цикл периодической проверки
    time.sleep(2)
    logger.info("old scheduler started")
    while True:
        raw_sql_checker()
        time.sleep(timeout_secs)


def raw_sql_checker():
    """Проверяет нужных докторов и отправляет всем желающим пользователям сообщение о наличи талончика"""
    active_docs_with_users = DB.get_active_doctors_joined_users()
    logger.debug("\nactive_docs_with_users: %s", active_docs_with_users)
    for doc_with_users in active_docs_with_users.values():
        # запрашиваем информацию о враче у горздрава
        api_doctor: Doctor | None = Gorzdrav.get_doctor(
            lpuId=doc_with_users.lpuId,
            specialtyId=doc_with_users.specialtyId,
            doctorId=doc_with_users.doctorId,
        )
        logger.debug(
            "api_doctor: %s",
            api_doctor.model_dump_json(indent=2) if api_doctor else None,
        )
        if api_doctor is None:
            continue

        if not api_doctor.have_free_places:
            continue

        link: str = Gorzdrav.generate_link(
            districtId=doc_with_users.districtId,
            lpuId=doc_with_users.lpuId,
            specialtyId=doc_with_users.specialtyId,
            scheduleId=doc_with_users.doctorId,
        )

        # проверяем надо ли получать назначения отдельно у доктора (если есть пользователи с лимитером)
        doctor_users = doc_with_users.pinging_users
        is_any_user_have_day_limit = [
            user for user in doctor_users if user.limit_days
        ].__len__() > 0
        appointments: list[ApiAppointment] = []
        if is_any_user_have_day_limit:
            # получаем назначения у доктора
            appointments = Gorzdrav.get_appointments(
                lpuId=doc_with_users.lpuId,
                doctorId=doc_with_users.doctorId,
            )
            logger.debug("doctor appointments: %s", appointments)

        message: str = TgMessageComposer.get_doc_ready_message_md(
            doctor_name=api_doctor.name,
            free_participant_count=api_doctor.freeParticipantCount,
            free_ticket_count=api_doctor.freeTicketCount,
            doctor_link=link,
            appointments=appointments,
        )

        for user in doc_with_users.pinging_users:
            logger.debug("user: %s", user.model_dump_json(indent=2))

            is_in_limit: bool = CheckerApp.check_appointments_in_user_limit_days(
                appointments=appointments,
                user=user,
            )
            if user.limit_days and (not is_in_limit):
                continue

            time.sleep(0.2)
            CheckerApp.send_tg_message(
                message=message,
                api_token=Config.BOT_TOKEN,
                chat_id=user.id,
                parse_mode=TGParseMode.MARKDOWN,
            )
            DB.set_user_ping_status(user_id=user.id, ping_status=False)


if __name__ == "__main__":
    old_scheduler(timeout_secs=Config.CHECKER_TIMEOUT_SECS)
