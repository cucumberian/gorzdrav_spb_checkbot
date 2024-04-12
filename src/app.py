from functools import wraps
import telebot
import multiprocessing

from queries.orm import SyncOrm
from config import Config
from gorzdrav import validate
from gorzdrav.api import Gorzdrav
import gorzdrav.models as api_models
from models import pydantic_models
from modules.db import SqliteDb
import checker


bot = telebot.TeleBot(token=Config.bot_token)
# gorzdrav = modules.net.GorzdravSpbAPI()

#####################
#
#
#
# 2024-04-08
# fixed: regex, чтобы соответствовать типам данных моделей api
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
        # user = SyncOrm.get_user(user_id=user_id)
        db = SqliteDb(file=Config.db_file)
        user = db.get_user(user_id=user_id)
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
        # doctor = SyncOrm.get_user_doctor(user_id=user_id)
        db = SqliteDb(file=Config.db_file)
        doctor = db.get_user_doctor(user_id=user_id)
        if not doctor:
            bot.reply_to(
                message=message,
                text="Пожалуйста добавьте врача.\n"
                + "Пришлите боту ссылку"
                + " полученную при выборе врача по адресу"
                + " https://gorzdrav.spb.ru/service-free-schedule#",
            )
            return None
        return func(message, *args, **kwargs)

    return wrapper


@bot.message_handler(commands=["start"])
def start_message(message):
    user_id = message.from_user.id
    db = SqliteDb(file=Config.db_file)
    db.delete_user(user_id=user_id)
    new_user = pydantic_models.DbUser(id=user_id)
    db.add_user(user=new_user)
    # SyncOrm.delete_user(user_id=user_id)
    # SyncOrm.add_user(user_id=user_id)
    bot.reply_to(
        message,
        "Ваш профиль создан.\n\n"
        + "Добавьте врача прислав ссылку со страницы его расписания"
        + " через свободную запись к врачу: \n"
        + "https://gorzdrav.spb.ru/service-free-schedule#\n\n"
        + "Используйте команду /delete для удаления профиля.",
    )


@bot.message_handler(commands=["help"])
def get_help(message):
    text = """/start - создать профиль пользователя
/status - узнать текущий статус талонов у врача
/on - включить отслеживание талонов
/off - отключить отслеживание талонов
/delete - удалить профиль пользователя

Пришлите боту ссылку расписания врача со страницы свободной записи (https://gorzdrav.spb.ru/service-free-schedule), чтобы добавить врача."""
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
    # SyncOrm.update_user(user_id=user_id, ping_status=True)
    db = SqliteDb(file=Config.db_file)
    db.set_user_ping_status(user_id=user_id, ping_status=True)
    bot.reply_to(message, "Отслеживание включено")


@bot.message_handler(commands=["off"])
@is_user_profile
@is_user_have_doctor
def ping_off(message):
    """
    Устанавливает статус проверки талонов для пользователя в False (Отключена).
    """
    user_id = message.from_user.id
    # SyncOrm.update_user(user_id=user_id, ping_status=False)
    db = SqliteDb(file=Config.db_file)
    db.set_user_ping_status(user_id=user_id, ping_status=False)
    bot.reply_to(message, "Отслеживание выключено")


@bot.message_handler(commands=["delete"])
@is_user_profile
def delete_user(message):
    """
    Удаляет профиль пользователя из базы данных.
    """
    user_id = message.from_user.id
    # SyncOrm.delete_user(user_id=user_id)
    db = SqliteDb(file=Config.db_file)
    db.delete_user(user_id=user_id)
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
    # user: db_models.UserOrm | None = SyncOrm.get_user(user_id=user_id)
    # user_doctor: db_models.DoctorOrm | None = SyncOrm.get_user_doctor(
    #     user_id=user_id
    # )
    db = SqliteDb(file=Config.db_file)
    user = db.get_user(user_id=user_id)
    user_doctor = db.get_user_doctor(user_id=user_id)
    gorzdrav_doctor: api_models.ApiDoctor | None = Gorzdrav.get_doctor(
        lpuId=user_doctor.lpuId,
        specialtyId=user_doctor.specialtyId,
        doctorId=user_doctor.doctorId,
    )
    if gorzdrav_doctor is None:
        doctor_url = Gorzdrav._Gorzdrav__get_doctors_endpoint(
            lpu_id=user_doctor.lpuId,
            specialty_id=user_doctor.specialtyId,
        )
        bot.reply_to(
            message=message,
            text=f"Не удалось получить данные врача по ссылке {doctor_url}\n"
            + "Попробуйте позднее или задайте снова врача.",
        )
        return None
    ping_text = (
        f"Отслеживание {'включено' if user.ping_status else 'отключено'}."
    )
    bot.reply_to(
        message=message,
        text=f"{gorzdrav_doctor}\n{ping_text}",
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
    parsing_result: (
        api_models.LinkParsingResult | None
    ) = validate.get_ids_from_gorzdrav_url(url=message.text)
    if parsing_result is None:
        bot.reply_to(
            message,
            "Не могу понять врача по ссылке.\n"
            + "Пожалуйста пришлите ссылку на врача, "
            + "как выберите его расписание.",
        )
        return None
    db = SqliteDb(file=Config.db_file)
    user_id: int = message.from_user.id

    api_doctor: api_models.Doctor | None = Gorzdrav.get_doctor(
        districtId=parsing_result.districtId,
        lpuId=parsing_result.lpuId,
        specialtyId=parsing_result.specialtyId,
        doctorId=parsing_result.doctorId,
    )
    if api_doctor is None:
        bot.reply_to(
            message,
            "Не удалось получить данные врача от горздрава.\n"
            + "Попробуйте позднее или задайте попробуйте другую ссылку.",
        )
        return None

    # добавляем врача в бд
    # doctor_id: str = SyncOrm.add_doctor(
    #     lpuId=parsing_result.lpuId,
    #     specialtyId=parsing_result.specialtyId,
    #     doctorId=parsing_result.doctorId,
    # )

    db_doctor = pydantic_models.DbDoctorToCreate(
        districtId=parsing_result.districtId,
        lpuId=parsing_result.lpuId,
        specialtyId=parsing_result.specialtyId,
        doctorId=parsing_result.doctorId,
    )
    doctor_id: str = db.add_doctor(doctor=db_doctor)
    # добавляем врача к пользователю
    # SyncOrm.update_user(user_id=user_id, doctor_id=doctor_id)
    db.add_user_doctor(user_id=user_id, doctor_id=doctor_id)
    user = db.get_user(user_id=user_id)
    ping_text = (
        f"Отслеживание {'включено' if user.ping_status else 'отключено'}."
    )
    bot.reply_to(
        message=message,
        text=f"Выбран врач {api_doctor.name}\n"
        + f"Свободных мест {api_doctor.freeParticipantCount}.\n"
        + f"Свободных талонов {api_doctor.freeTicketCount}.\n"
        + "\n"
        + f"{ping_text}\n",
    )


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
    checker = multiprocessing.Process(
        target=checker.old_checker,
        name="gorzdrav_checker",
        kwargs={},
        daemon=True,
    )
    checker.start()
    bot.polling(none_stop=True)
