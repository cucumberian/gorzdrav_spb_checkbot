import requests
import time
from pprint import pprint

from gorzdrav.api import Gorzdrav
from models import pydantic_models
from config import Config
from queries.orm import SyncOrm
import db.models as db_models

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
    requests.post(url, data=data)


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
    print("checker iteration")
    free_doctors_dict = collect_free_doctors()
    # pprint(f"{free_doctors_dict = }")
    pinged_users: list[db_models.UserOrm] = SyncOrm.get_users(ping_status=True)
    for user in pinged_users:
        user_doctor = free_doctors_dict.get(user.doctor_id, None)
        if not user_doctor:
            # если для пользователя нет врачей
            # со свободными назначениями пропускаем
            continue
        user_doctor["users"].append(user)
    # pprint(f"{free_doctors_dict = }")

    for free_doc_id, free_doc_data in free_doctors_dict.items():
        free_doc_users = free_doc_data["users"]
        print(f"{free_doc_id = }")
        appointments_count = len(free_doc_data["appointments"])
        for user in free_doc_users:
            pprint(f"{user = }")
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
