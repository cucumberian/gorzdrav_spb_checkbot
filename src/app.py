from functools import wraps
from typing import Any, Callable
import multiprocessing

from pydantic import BaseModel


import telebot  # type: ignore
from telebot.types import Message  # type: ignore
from telebot.types import InaccessibleMessage  # type: ignore
from telebot.types import CallbackQuery  # type: ignore
from telebot.storage import StateMemoryStorage  # type: ignore
# from telebot.states.sync.context import StateContext

from telebot.types import InlineKeyboardMarkup  # type: ignore
from telebot.types import InlineKeyboardButton  # type: ignore

from config import Config
from gorzdrav.api import Gorzdrav
import gorzdrav.models as api_models
from models import pydantic_models
from modules.db import SqliteDb
import checker


from states.states import StateManager as SM
from states.states import MiState
from states.states import STATES_NAMES


state_storage = StateMemoryStorage()  # хранилище для состояний в памяти

bot = telebot.TeleBot(
    token=Config.bot_token,
    state_storage=state_storage,
    use_class_middlewares=True,
)


# gorzdrav = modules.net.GorzdravSpbAPI()

#####################
#
# 2025-04-06
# feat: простой стейт менеджер чтобы выбирать врачей через бота, а не через сайт
#
# 2024-04-08
# fixed: regex, чтобы соответствовать типам данных моделей api
#
#
######################


class KeySchema(BaseModel):
    text: str
    callback_data: str


def get_keyboard(keys: list[KeySchema]) -> InlineKeyboardMarkup:
    def get_key_text(text: str, max_len: int = 100):
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    kb = InlineKeyboardMarkup()
    for key in keys:
        btn = InlineKeyboardButton(
            text=get_key_text(key.text),
            callback_data=key.callback_data,
        )
        kb.add(btn)  # type: ignore
    # kb.add(InlineKeyboardButton(text="Закрыть", callback_data="close"))
    return kb


def is_user_profile(func: Callable):
    """
    Декоратор для проверки наличия профиля пользователя.
    Если профиля нет, то отправляет сообщение об ошибке и возвращает None.
    """

    @wraps(func)
    def wrapper(message: Message, *args, **kwargs):
        if message.from_user is None:
            return None
        user_id = message.from_user.id
        # user = SyncOrm.get_user(user_id=user_id)
        db = SqliteDb(file=Config.db_file)
        user = db.get_user(user_id=user_id)
        if not user:
            bot.reply_to(  # type: ignore
                message,
                "У вас нет профиля.\n"
                + "Используйте команду /start для создания профиля.",
            )
            # состояние бота на "нет профиля"
            SM.set_state(user_id=user_id, state_name=STATES_NAMES.NO_PROFILE)
            return
        current_state = SM.get_state(user_id)
        if current_state.name == STATES_NAMES.UNDEFINED:
            current_state = MiState(name=STATES_NAMES.HAVE_PROFILE)
        return func(message, *args, **kwargs)

    return wrapper


def is_user_have_doctor(func: Callable):
    """
    Декоратор для проверки наличия врача у пользователя.
    Если врача нет, то отправляет сообщение об ошибке и возвращает None.
    """

    @wraps(func)
    def wrapper(message_or_callback: Message | CallbackQuery, *args, **kwargs):
        if isinstance(message_or_callback, Message):
            message = message_or_callback
        else:
            message = message_or_callback.message
        user_id = message.from_user.id
        # doctor = SyncOrm.get_user_doctor(user_id=user_id)
        db = SqliteDb(file=Config.db_file)
        doctor = db.get_user_doctor(user_id=user_id)
        if not doctor:
            bot.reply_to(
                message=message,
                text="Пожалуйста добавьте врача.\n" + "Выполните команду /set_doctor",
            )
            return None
        return func(message, *args, **kwargs)

    return wrapper


def is_state(
    allowed_states_names: list[STATES_NAMES],
    restricted_states_names: list[STATES_NAMES] | None = None,
):
    """
    Декоратор для проверки состояния бота.
    Если состояние не соответствует заданному, то отправляет сообщение об ошибке и возвращает None.
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(message_or_callback: Message | CallbackQuery, *args, **kwargs):
            user_id = message_or_callback.from_user.id
            current_state = SM.get_state(user_id)
            if (
                restricted_states_names
                and current_state.name in restricted_states_names
            ):
                return None
            elif current_state.name not in allowed_states_names:
                return None
            return func(message_or_callback, *args, **kwargs)

        return wrapper

    return decorator


@bot.callback_query_handler(func=lambda call: call.data == "close")  # type: ignore
def close_message(call: CallbackQuery):
    bot.delete_message(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )


@bot.message_handler(commands=["start"])  # type: ignore
def start_message(message: Message):
    if message.from_user is None:
        return
    user_id = message.from_user.id
    db = SqliteDb(file=Config.db_file)
    db.delete_user(user_id=user_id)
    SM.set_state(user_id=user_id, state_name=STATES_NAMES.NO_PROFILE)

    new_user = pydantic_models.DbUser(id=user_id)
    db.add_user(user=new_user)
    SM.set_state(user_id=user_id, state_name=STATES_NAMES.HAVE_PROFILE)

    # устанавливаем состояние бота
    # bot.set_state(
    #     user_id=user_id,
    #     state="have_profile",
    # )
    # state.set(state=UserState.have_profile)

    # SyncOrm.delete_user(user_id=user_id)
    # SyncOrm.add_user(user_id=user_id)
    bot.reply_to(  # type: ignore
        message,
        "Ваш профиль создан.\n\n"
        + "Используйте команду /set_doctor для выбора врача.\n"
        + "Используйте команду /delete для удаления профиля.",
    )


@bot.message_handler(commands=["help"])  # type: ignore
def get_help(message: Message):
    text = (
        "/start - создать профиль пользователя\n"
        + "/status - узнать текущий статус талонов у врача\n"
        + "/on - включить отслеживание талонов\n"
        + "/off - отключить отслеживание талонов\n"
        + "/delete - удалить профиль пользователя\n"
        + "/state - узнать текущее состояние бота\n\n"
        + "/set_doctor - выбрать врача и медицинское учреждение"
    )
    bot.reply_to(message, text)  # type: ignore


def back_to_state(
    message: Message | InaccessibleMessage,
    state_name: STATES_NAMES,
    payload: dict[str, Any] | None = None,
):
    if message.from_user is None:
        return
    user_id = message.from_user.id
    bot.delete_message(
        chat_id=message.chat.id,
        message_id=message.message_id,
    )
    SM.set_state(user_id=user_id, state_name=state_name, payload=payload)


@bot.message_handler(commands=["set_doctor"])  # type: ignore
@is_user_profile
def start_set_doctor(message: Message):
    if message.from_user is None:
        return
    user_id = message.from_user.id
    districts = Gorzdrav.get_districts()

    keys: list[KeySchema] = []
    for district in districts:
        keys.append(
            KeySchema(
                text=f"{district.name}",
                callback_data=f"district/{district.id}",
            )
        )
    keys.append(KeySchema(text="Назад", callback_data="district/back"))
    bot.reply_to(  # type: ignore
        message,
        "Выберите район:",
        reply_markup=get_keyboard(keys),
    )
    SM.set_state(
        user_id=user_id,
        state_name=STATES_NAMES.SELECT_DISTRICT,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("district/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_DISTRICT])
def set_district(call: CallbackQuery):
    if not call.data:
        return
    user_id = call.from_user.id
    command = call.data.split("/")[1]

    if command == "back":
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        SM.set_state(
            user_id=user_id,
            state_name=STATES_NAMES.HAVE_PROFILE,
            payload={},
        )
        return

    district_id = command

    # установка выбранного состояния
    SM.set_state(
        user_id=user_id,
        state_name=STATES_NAMES.SELECT_LPU,
        payload={"district_id": district_id},
    )

    lpus = Gorzdrav.get_lpus(districtId=district_id)

    keys: list[KeySchema] = []
    for lpu in lpus:
        keys.append(
            KeySchema(
                text=f"{lpu.lpuFullName} - {lpu.address}",
                callback_data=f"lpu/{lpu.id}",
            )
        )
    keys.append(KeySchema(text="Назад", callback_data="lpu/back"))

    bot.send_message(
        chat_id=call.message.chat.id,
        text="Выберите медучреждение:",
        reply_markup=get_keyboard(keys),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("lpu/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_LPU])
def set_lpu(call: CallbackQuery):
    if not call.data:
        return
    user_id = call.from_user.id
    state = SM.get_state(user_id)
    state_payload = state.payload
    command = call.data.split("/")[1]

    if command == "back":
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        SM.set_state(
            user_id=user_id,
            state_name=STATES_NAMES.SELECT_DISTRICT,
            payload={},
        )
        return

    lpu_id = command
    lpu = Gorzdrav.get_lpu(lpuId=int(lpu_id))

    # установка состояния
    state_payload["lpu"] = lpu
    SM.set_state(
        user_id=user_id,
        state_name=STATES_NAMES.SELECT_SPECIALTY,
        payload=state_payload,
    )

    specialties = Gorzdrav.get_specialties(lpuId=int(lpu_id))

    keys: list[KeySchema] = []
    for specialty in specialties:
        keys.append(
            KeySchema(
                text=f"{specialty.name}",
                callback_data=f"specialty/{specialty.id}",
            )
        )
    keys.append(KeySchema(text="Назад", callback_data="specialty/back"))
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Выберите специальность в медучреждении {lpu.lpuFullName}:",
        reply_markup=get_keyboard(keys),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("specialty/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_SPECIALTY])
def set_specialty(call: CallbackQuery):
    if call.data is None:
        return
    user_id = call.from_user.id
    state = SM.get_state(user_id)
    state_payload = state.payload

    command = call.data.split("/")[1]

    if command == "back":
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        del state_payload["lpu"]
        SM.set_state(
            user_id=user_id,
            state_name=STATES_NAMES.SELECT_LPU,
            payload=state_payload,
        )
        return

    specialty_id = command

    lpu = state_payload["lpu"]
    doctors = Gorzdrav.get_doctors(lpuId=lpu.id, specialtyId=specialty_id)
    keys: list[KeySchema] = []
    for doc in doctors:
        keys.append(
            KeySchema(
                text=f"[{doc.freeParticipantCount}:{doc.freeTicketCount}] {doc.name}",
                callback_data=f"doctor/{doc.id}",
            )
        )
    keys.append(KeySchema(text="Назад", callback_data="doctor/back"))
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Выберите врача в медучреждении {lpu.lpuFullName}:",
        reply_markup=get_keyboard(keys),
    )

    state_payload["specialty_id"] = specialty_id
    SM.set_state(
        user_id=user_id,
        state_name=STATES_NAMES.SELECT_DOCTOR,
        payload=state_payload,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("doctor/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_DOCTOR])
def set_doctor(call: CallbackQuery):
    if call.data is None:
        return
    user_id = call.from_user.id
    state = SM.get_state(user_id)
    state_payload = state.payload

    command = call.data.split("/")[1]

    if command == "back":
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        del state_payload["specialty_id"]
        SM.set_state(
            user_id=user_id,
            state_name=STATES_NAMES.SELECT_SPECIALTY,
            payload=state_payload,
        )
        return

    doctor_id = command

    district_id: str = state_payload["district_id"]
    lpu: api_models.ApiLPU = state_payload["lpu"]
    specialty_id = state_payload["specialty_id"]

    doctor = Gorzdrav.get_doctor(
        lpuId=lpu.id,
        specialtyId=specialty_id,
        doctorId=doctor_id,
    )
    if doctor is None:
        bot.send_message(
            chat_id=call.message.chat.id,
            text="Не удалось получить информацию о враче. Попробуйте еще раз.",
        )
        return

    db = SqliteDb(file=Config.db_file)

    db_doctor = pydantic_models.DbDoctorToCreate(
        districtId=district_id,
        lpuId=lpu.id,
        specialtyId=specialty_id,
        doctorId=doctor_id,
    )
    doctor_id = db.add_doctor(doctor=db_doctor)
    db.add_user_doctor(user_id=user_id, doctor_id=doctor_id)

    SM.set_state(user_id=user_id, state_name=STATES_NAMES.HAVE_PROFILE)

    user = db.get_user(user_id=user_id)
    if user is None:
        return
    ping_text = f"Отслеживание {'включено' if user.ping_status else 'отключено'}."
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Выбран врач {doctor.name}\n"
        + f"Свободных мест {doctor.freeParticipantCount}.\n"
        + f"Свободных талонов {doctor.freeTicketCount}.\n"
        + "\n"
        + f"{ping_text}\n",
    )


@bot.message_handler(commands=["id"])  # type: ignore
def id_message(message: Message):
    """
    Пишет пользователю его telegram id.
    """
    bot.send_message(message.chat.id, "Ваш telegram id: " + str(message.chat.id))


@bot.message_handler(commands=["on"])  # type: ignore
@is_user_profile
@is_user_have_doctor
def ping_on(message: Message):
    """
    Устанавливает статус проверки талонов для пользователя в True (Включена).
    """
    if message.from_user is None:
        return
    user_id = message.from_user.id
    # SyncOrm.update_user(user_id=user_id, ping_status=True)
    db = SqliteDb(file=Config.db_file)
    db.set_user_ping_status(user_id=user_id, ping_status=True)
    bot.reply_to(message, "Отслеживание включено")  # type: ignore


@bot.message_handler(commands=["off"])  # type: ignore
@is_user_profile
@is_user_have_doctor
def ping_off(message: Message):
    """
    Устанавливает статус проверки талонов для пользователя в False (Отключена).
    """
    if message.from_user is None:
        return
    user_id = message.from_user.id
    # SyncOrm.update_user(user_id=user_id, ping_status=False)
    db = SqliteDb(file=Config.db_file)
    db.set_user_ping_status(user_id=user_id, ping_status=False)
    bot.reply_to(message, "Отслеживание выключено")  # type: ignore


@bot.message_handler(commands=["delete"])  # type: ignore
@is_user_profile
def delete_user(message: Message):
    """
    Удаляет профиль пользователя из базы данных.
    """
    if message.from_user is None:
        return
    user_id = message.from_user.id

    db = SqliteDb(file=Config.db_file)
    db.delete_user(user_id=user_id)
    SM.set_state(user_id, STATES_NAMES.NO_PROFILE)
    bot.reply_to(  # type: ignore
        message,
        "Ваш профиль удалён.\n" + "Выполните команду /start за создания профиля.",
    )


@bot.message_handler(commands=["status"])  # type: ignore
@is_user_profile
@is_user_have_doctor
def get_status(message: Message):
    """
    Пишет пользователю информацию о его враче.
    """
    if message.from_user is None:
        return
    user_id = message.from_user.id
    db = SqliteDb(file=Config.db_file)
    user = db.get_user(user_id=user_id)
    if user is None:
        return
    user_doctor = db.get_user_doctor(user_id=user_id)
    if user_doctor is None:
        return
    gorzdrav_doctor: api_models.ApiDoctor | None = Gorzdrav.get_doctor(
        lpuId=user_doctor.lpuId,
        specialtyId=user_doctor.specialtyId,
        doctorId=user_doctor.doctorId,
    )
    if gorzdrav_doctor is None:
        bot.reply_to(  # type: ignore
            message=message,
            text="Не удалось получить данные врача.\n"
            + "Попробуйте позднее или задайте снова врача командой /set_doctor.",
        )
        return None
    ping_text = f"Отслеживание {'включено' if user.ping_status else 'отключено'}."
    bot.reply_to(  # type: ignore
        message=message,
        text=f"{gorzdrav_doctor}\n{ping_text}",
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
    print("Bot supports_inline_queries: " + str(bot.get_me().supports_inline_queries))
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
