import logging
import time
from enum import StrEnum

import requests
from pydantic import BaseModel

from config import Config
import db.models as db_models
from depends import sqlite_db as DB
from gorzdrav.api import Gorzdrav
from gorzdrav.models import ApiAppointment, Doctor
from queries.orm import SyncOrm
from telegram.message_composer import TgMessageComposer

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

SyncOrm.create_tables()


class TGParseMode(StrEnum):
    HTML = "html"
    MARKDOWN = "Markdown"


# send message to telegram with requests.post
def send_message(
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
    url = f"https://api.telegram.org/bot{api_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }
    response = requests.post(
        url,
        data=data,
        params={"parse_mode": parse_mode},
    )
    if not response.ok:
        print(f"Failed to send message to {chat_id}", response.text)


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
            send_message(message=text, api_token=Config.BOT_TOKEN, chat_id=user.id)
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
    logger.debug("active_docs_with_users: %s", active_docs_with_users)
    for doc_with_users in active_docs_with_users.values():
        # запрашиваем информацию о враче у горздрава
        api_doctor: Doctor | None = Gorzdrav.get_doctor(
            lpuId=doc_with_users.lpuId,
            specialtyId=doc_with_users.specialtyId,
            doctorId=doc_with_users.doctorId,
        )
        if api_doctor is None:
            continue
        if api_doctor.have_free_places:
            link = Gorzdrav.generate_link(
                districtId=doc_with_users.districtId,
                lpuId=doc_with_users.lpuId,
                specialtyId=doc_with_users.specialtyId,
                scheduleId=doc_with_users.doctorId,
            )
            message = TgMessageComposer.get_doc_ready_message_md(
                doctor_name=api_doctor.name,
                free_participant_count=api_doctor.freeParticipantCount,
                free_ticket_count=api_doctor.freeTicketCount,
                doctor_link=link,
            )

            for user in doc_with_users.pinging_users:
                logger.debug("user: %s", user.model_dump_json(indent=2))

                time.sleep(0.2)
                send_message(
                    message=message,
                    api_token=Config.BOT_TOKEN,
                    chat_id=user.id,
                    parse_mode=TGParseMode.MARKDOWN,
                )
                DB.set_user_ping_status(user_id=user.id, ping_status=False)
