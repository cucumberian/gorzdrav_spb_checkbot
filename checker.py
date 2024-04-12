import requests
import time

from gorzdrav.api import Gorzdrav
import gorzdrav.models as api_models
from models import pydantic_models
from config import Config
from queries.orm import SyncOrm
import db.models as db_models

from modules.db import SqliteDb
from config import Config

SyncOrm.create_tables()


# send message to telegram with requests.post
def send_message(message: str, api_token: str, chat_id: int | str) -> None:
    """
    Отправка сообщений в телеграм пользователю через requests.post
    :param message: str - сообщение
    :param api_token: str - токен бота
    :param chat_id: - id чата
    :return: None
    """
    url = f"https://api.telegram.org/bot{api_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=data)
    if not response.ok:
        print(f"Failed to send message to {chat_id}", response.text)


def collect_free_doctors() -> dict[str : {}]:
    pinged_doctors: list[db_models.Doctor] = SyncOrm.get_pinged_doctors()
    free_doctors_dict = {}
    for doc in pinged_doctors:
        appointments: list[
            pydantic_models.ApiAppointment
        ] = Gorzdrav.get_appointments(
            lpu_id=doc.lpuId,
            doctor_id=doc.doctorId,
        )
        if appointments:
            free_doctors_dict[doc.id] = {
                "appointments": appointments,
                "users": [],
            }
    return free_doctors_dict


def checker():
    free_doctors_dict = collect_free_doctors()
    pinged_users: list[db_models.UserOrm] = SyncOrm.get_users(ping_status=True)
    for user in pinged_users:
        user_doctor = free_doctors_dict.get(user.doctor_id, None)
        if not user_doctor:
            # если для пользователя нет врачей
            # со свободными назначениями пропускаем
            continue
        user_doctor["users"].append(user)

    for free_doc_id, free_doc_data in free_doctors_dict.items():
        free_doc_users = free_doc_data["users"]
        appointments_count = len(free_doc_data["appointments"])
        for user in free_doc_users:
            text = f"У вашего врача {appointments_count} свободных талонов"
            send_message(
                message=text, api_token=Config.bot_token, chat_id=user.id
            )
            # отключаем пинг для пользователя после отправки сообщений
            SyncOrm.update_user(user_id=user.id, ping_status=False)
            time.sleep(0.1)


def scheduler():
    timeout_secs = Config.checker_timeout_secs or 300

    while True:
        checker()
        time.sleep(timeout_secs)


if __name__ == "__main__":
    scheduler()


def old_checker(timeout_secs: int = 120):
    time.sleep(2)
    db = SqliteDb(file=Config.db_file)

    while True:
        active_doctors = db.get_active_doctors()
        for active_doctor in active_doctors:
            time.sleep(0.2)
            doctor = Gorzdrav.get_doctor(
                districtId=active_doctor.districtId,
                lpuId=active_doctor.lpuId,
                specialtyId=active_doctor.specialtyId,
                doctorId=active_doctor.doctorId,
            )
            if doctor is None:
                continue

            if doctor.is_free:
                link = Gorzdrav.generate_link(
                    districtId=doctor.districtId,
                    lpuId=doctor.lpuId,
                    specialtyId=doctor.specialtyId,
                    scheduleId=doctor.doctorId,
                )
                message = (
                    f"Врач {doctor.name} доступен для записи.\n"
                    + f"Талонов для записи: {doctor.freeTicketCount}, "
                    + f"мест: {doctor.freeParticipantCount}\n\n"
                    + f"Запишитесь на приём по ссылке: {link}\n\n"
                    + "Отслеживание отключено."
                )

                users = db.get_users_by_doctor(doctor_id=active_doctor.id)
                for user in users:
                    time.sleep(0.2)
                    send_message(
                        message=message,
                        api_token=Config.bot_token,
                        chat_id=user.id,
                    )
                    db.set_user_ping_status(user_id=user.id, ping_status=False)

        time.sleep(timeout_secs)
