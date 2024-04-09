from functools import wraps
import telebot

from queries.orm import SyncOrm
from config import Config
from modules import validate
from gorzdrav.api import Gorzdrav
from models import pydantic_models
from db import models as db_modelspyth

print(f"{Config.bot_token = }")
bot = telebot.TeleBot(token=Config.bot_token)
# gorzdrav = modules.net.GorzdravSpbAPI()

#####################
#
#
#
# 2024-04-08
# fixed: regex, чтобы соответствовать типам данных модели api
#
#
######################


def is_user_profile(func):
    """
    Декоратор для проверки наличия профиля пользователя.
    Если профиля нет, то отправляет сообщение об ошибке и возвращает None.
    """

    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        user = SyncOrm.get_user(user_id=user_id)
        if not user:
            bot.reply_to(
                message,
                "У вас нет профиля.\n"
                + "Используйте команду /start для создания профиля.",
            )
            return
        return func(message, *args, **kwargs)

    return wrapper


def is_user_have_doctor(func):
    """
    Декоратор для проверки наличия врача у пользователя.
    Если врача нет, то отправляет сообщение об ошибке и возвращает None.
    """

    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        doctor = SyncOrm.get_user_doctor(user_id=user_id)
        if not doctor:
            bot.reply_to(
                message=message,
                text="Пожалуйста добавьте врача.\n"
                + "Пришлите боту ссылку"
                + " с сайта https://gorzdrav.spb.ru/ с врачом.",
            )
            return None
        return func(message, *args, **kwargs)

    return wrapper


@bot.message_handler(commands=["start"])
def start_message(message):
    user_id = message.from_user.id
    SyncOrm.delete_user(user_id=user_id)
    SyncOrm.add_user(user_id=user_id)
    bot.reply_to(
        message,
        "Ваш профиль создан.\n"
        + "Используйте команду \delete для удаления профиля.",
    )


@bot.message_handler(commands=["help"])
def get_help(message):
    text = """/start - создать профиль пользователя
/status - узнать текущий статус талонов у врача
/on - включить отслеживание талонов
/off - отключить отслеживание талонов
/delete - удалить профиль пользователя

# Пришлите боту ссылку с горздрава на врача, чтобы его наблюдать."""
    bot.reply_to(message, text)


@bot.message_handler(commands=["id"])
def id_message(message):
    """
    Пишет пользователю его telegram id.
    """
    bot.send_message(
        message.chat.id, "Ваш telegram id: " + str(message.chat.id)
    )


@bot.message_handler(commands=["on"])
@is_user_profile
@is_user_have_doctor
def ping_on(message):
    """
    Устанавливает статус проверки талонов для пользователя в True (Включена).
    """
    user_id = message.from_user.id
    SyncOrm.update_user(user_id=user_id, ping_status=True)
    bot.reply_to(message, "Проверка включена")


@bot.message_handler(commands=["off"])
@is_user_profile
@is_user_have_doctor
def ping_off(message):
    """
    Устанавливает статус проверки талонов для пользователя в False (Отключена).
    """
    user_id = message.from_user.id
    SyncOrm.update_user(user_id=user_id, ping_status=False)
    bot.reply_to(message, "Проверка выключена")


@bot.message_handler(commands=["delete"])
@is_user_profile
def delete_user(message):
    """
    Удаляет профиль пользователя из базы данных.
    """
    user_id = message.from_user.id
    SyncOrm.delete_user(user_id=user_id)
    bot.reply_to(
        message,
        "Ваш профиль удалён.\n"
        + "Выполните команду /start за создания профиля.",
    )


@bot.message_handler(commands=["status"])
@is_user_profile
@is_user_have_doctor
def get_status(message):
    """
    Пишет пользователю информацию о его враче.
    """
    user_id = message.from_user.id
    user: db_models.UserOrm | None = SyncOrm.get_user(user_id=user_id)
    user_doctor: db_models.DoctorOrm | None = SyncOrm.get_user_doctor(
        user_id=user_id
    )
    gorzdrav_doctor: pydantic_models.ApiDoctor | None = Gorzdrav.get_doctor(
        lpuId=user_doctor.lpuId,
        specialtyId=user_doctor.specialtyId,
        doctorId=user_doctor.doctorId,
    )
    if not gorzdrav_doctor:
        doctor_url = Gorzdrav._Gorzdrav__get_doctors_endpoint(
            lpu_id=user_doctor.lpuId,
            specialty_id=user_doctor.specialtyId,
        )
        bot.reply_to(
            message=message,
            text=f"Не удалось получить данные врача по ссылке {doctor_url}\n"
            + "Попробуйте позднее или задайте снова врача.",
        )
        return
    bot.reply_to(
        message=message, text=f"{gorzdrav_doctor}\n" + user.ping_status_str
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda m: validate.is_domain(m.text) or validate.is_url(m.text),
)
@is_user_profile
def get_url(message):
    """
    Получем ссылку на врача и добавляем в бд
    Если ссылка не валидна, то сигнализируем пользователю.
    """
    print(f"{message.text = }")
    parsing_result: dict | None = validate.get_ids_from_gorzdrav_url(
        url=message.text
    )
    print(f"{parsing_result = }")
    if not parsing_result:
        bot.reply_to(
            message,
            "Не могу понять врача по ссылке. \
            Пожалуйста пришлите ссылку на врача, как выберите его расписание.",
        )
        return
    lpuId = parsing_result["lpuId"]
    specialtyId = parsing_result["specialtyId"]
    doctorId = parsing_result["doctorId"]
    user_id: int = message.from_user.id

    doctor: pydantic_models.ApiDoctor | None = Gorzdrav.get_doctor(
        lpuId=lpuId, specialtyId=specialtyId, doctorId=doctorId
    )
    bot.reply_to(message=message, text=f"{doctor}")
    # добавляем врача в бд
    doctor_id: str = SyncOrm.add_doctor(
        lpuId=lpuId,
        specialtyId=specialtyId,
        doctorId=doctorId,
    )
    # добавляем врача к пользователю
    SyncOrm.update_user(user_id=user_id, doctor_id=doctor_id)


if __name__ == "__main__":
    print("Bot start")
    print("Bot username: " + str(bot.get_me().username))
    print("Bot id: " + str(bot.get_me().id))
    print("Bot first_name: " + bot.get_me().first_name)
    print("Bot can_join_groups: " + str(bot.get_me().can_join_groups))
    print(
        "Bot can_read_all_group_messages: "
        + str(bot.get_me().can_read_all_group_messages)
    )
    print(
        "Bot supports_inline_queries: "
        + str(bot.get_me().supports_inline_queries)
    )
    print("Bot started")

    # запускаем процесс с отправкой уведомлений
    # теперь работает через докер
    # checker = multiprocessing.Process(
    #     target=checker,
    #     name="gorzdrav_checker",
    #     kwargs={
    #         "bot_token": Config.bot_token,
    #         "timeout_secs": Config.checker_timeout_secs,
    #         "db_file": Config.db_file,
    #     },
    #     daemon=True,
    # )
    # checker.start()

    bot.polling(none_stop=True)
