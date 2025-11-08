import logging
import time

from pydantic import BaseModel

import db.models as db_models
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


class FreeDoctor(BaseModel):
    appointments: list[ApiAppointment]
    users: list["UserOrm"]


def collect_free_doctors() -> dict[int, FreeDoctor]:
    """Возвращает словарь пингуемых докторов со свободными местами"""
    pinged_doctors: list[db_models.DoctorOrm] = SyncOrm.get_pinged_doctors()
    free_doctors_dict = {}
    for doc in pinged_doctors:
        appointments: list[ApiAppointment] = Gorzdrav.get_appointments(
            lpuId=doc.lpuId,
            doctorId=doc.doctorId,
        )
        if appointments:
            free_doctors_dict[doc.id] = FreeDoctor(
                appointments=appointments,
                users=[],
            )
    return free_doctors_dict


def checker():
    free_doctors_dict: dict[int, FreeDoctor] = collect_free_doctors()
    pinged_users: list[db_models.UserOrm] = SyncOrm.get_users(ping_status=True)
    for user in pinged_users:
        user_doctor_id = user.doctor_id
        if user_doctor_id is None:
            continue
        user_doctor = free_doctors_dict.get(user_doctor_id, None)
        if not user_doctor:
            # если для пользователя нет врачей
            # со свободными назначениями пропускаем
            continue
        user_doctor.users.append(user)

    for free_doc_id, free_doc_data in free_doctors_dict.items():
        free_doc_users = free_doc_data.users
        appointments_count = len(free_doc_data.appointments)
        for user in free_doc_users:
            text = f"У вашего врача {appointments_count} свободных талонов"
            CheckerApp.send_tg_message(
                message=text, api_token=Config.BOT_TOKEN, chat_id=user.id
            )
            # отключаем пинг для пользователя после отправки сообщений
            SyncOrm.update_user(user_id=user.id, ping_status=False)
            time.sleep(0.1)


def scheduler():
    timeout_secs = Config.CHECKER_TIMEOUT_SECS or 300

    while True:
        checker()
        time.sleep(timeout_secs)


if __name__ == "__main__":
    scheduler()


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
    logger.warning("\nactive_docs_with_users: %s", active_docs_with_users)
    for doc_with_users in active_docs_with_users.values():
        # запрашиваем информацию о враче у горздрава
        api_doctor: Doctor | None = Gorzdrav.get_doctor(
            lpuId=doc_with_users.lpuId,
            specialtyId=doc_with_users.specialtyId,
            doctorId=doc_with_users.doctorId,
        )
        logger.warning(
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
            print("doctor appointmrents", appointments)

        message: str = TgMessageComposer.get_doc_ready_message_md(
            doctor_name=api_doctor.name,
            free_participant_count=api_doctor.freeParticipantCount,
            free_ticket_count=api_doctor.freeTicketCount,
            doctor_link=link,
            appointments=appointments,
        )

        for user in doc_with_users.pinging_users:
            logger.info("user: %s", user.model_dump_json(indent=2))

            is_in_limit: bool = CheckerApp.check_appointments_in_user_limit_days(
                appointments=appointments,
                user=user,
            )
            if not is_in_limit:
                continue

            time.sleep(0.2)
            CheckerApp.send_tg_message(
                message=message,
                api_token=Config.BOT_TOKEN,
                chat_id=user.id,
                parse_mode=TGParseMode.MARKDOWN,
            )
            DB.set_user_ping_status(user_id=user.id, ping_status=False)
