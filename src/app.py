import logging
import multiprocessing
from functools import wraps
from typing import Any, Callable

import telebot
from pydantic import BaseModel
from telebot.storage import StateMemoryStorage
from telebot.types import (
    CallbackQuery,
    InaccessibleMessage,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from telebot.util import extract_command, is_command

import checker
import gorzdrav.models as api_models
from config import Config
from depends import sqlite_db as DB
from gorzdrav.api import Gorzdrav
from gorzdrav.exceptions import GorzdravExceptionBase
from keyboard_service import ButtonSchema, KeyboardService
from models import pydantic_models
from models.pydantic_models import DbUser
from states.states import STATES_NAMES, MiState
from states.states import StateManager as SM

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


state_storage = StateMemoryStorage()  # хранилище для состояний в памяти
keyboard_service = KeyboardService(page_size=10)

bot = telebot.TeleBot(
    token=Config.BOT_TOKEN,
    state_storage=state_storage,
    use_class_middlewares=True,
)


class KeySchema(BaseModel):
    text: str
    callback_data: str


def get_keyboard(keys: list[KeySchema], max_buttons: int = 50) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру по списку клавиш"""

    def get_key_text(text: str, max_len: int = 50):
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    def is_valid_callback_data(callback_data: str, max_len: int = 64):
        return len(callback_data.encode("utf-8")) <= max_len

    kb = InlineKeyboardMarkup()
    total_size = 0
    for key in keys[:max_buttons]:
        if not is_valid_callback_data(key.callback_data):
            continue

        btn = InlineKeyboardButton(
            text=get_key_text(key.text),
            callback_data=key.callback_data,
        )
        kb.add(btn)  # type: ignore

        if btn.callback_data is None:
            continue
        total_size += (
            len(btn.text.encode("utf-8")) + len(btn.callback_data.encode("utf-8")) + 20
        )
        if total_size >= 10 * 1024:
            break

    return kb


def handle_gorzdrav_exceptions(func):
    @wraps(func)
    def wrapper(message_or_callback: Message | CallbackQuery, *args, **kwargs):
        try:
            return func(message_or_callback, *args, **kwargs)
        except GorzdravExceptionBase as e:
            if isinstance(message_or_callback, Message):
                message = message_or_callback
            else:
                message = message_or_callback.message
            logger.error(f"Ошибка в API Gorzdrav: {e.message}")
            bot.send_message(
                chat_id=message.chat.id,
                text="Произошла ошибка при обращении к API Gorzdrav.\n"
                + str(e.message),
            )

    return wrapper


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

        user = DB.get_user(user_id=user_id)
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

        doctor = DB.get_user_doctor(user_id=user_id)
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
            if not message_or_callback.from_user:
                return None
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


# установка лимита дней для поиска свободных мест
@bot.message_handler(regexp=Config.LIMIT_DAYS_REGEX)
def get_set_limit_command(message: Message):
    tg_user = message.from_user
    if tg_user is None:
        return
    user_id = tg_user.id

    assert message.text

    if not is_command(text=message.text):
        return
    command = extract_command(message.text)

    assert command
    days_count = int(command)

    if days_count < 1:
        days_count = None  # сбрасываем количество дней у пользователя

    DB.set_limit_days(user_id=user_id, limit_days=days_count)
    db_user: DbUser | None = DB.get_user(user_id=user_id)
    if db_user is None:
        bot.reply_to(
            message=message, text="Пользователь не найден. Зарегистрируйтесь /start"
        )
        return

    if db_user.limit_days is not None:
        bot.reply_to(
            message=message,
            text=f"Установлено кол-во дней для проверки свободных мест: {db_user.limit_days}",
        )
    else:
        bot.reply_to(
            message=message,
            text="Сброшено кол-во дней для проверки свободных мест",
        )


@bot.message_handler(commands=["start"])  # type: ignore
def start_message(message: Message):
    if message.from_user is None:
        return
    user_id = message.from_user.id
    DB.delete_user(user_id=user_id)
    SM.set_state(user_id=user_id, state_name=STATES_NAMES.NO_PROFILE)

    new_user = pydantic_models.DbUser(id=user_id)
    DB.add_user(user=new_user)
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
        + "/1 - установить просмотр мест в течении сегодняшнего дня\n"
        + "/7 - установить просмотр мест в течении недели\n"
        + "/n - установить просмотр мест в течении n-дней\n"
        + "/0 - искать свободные места в любое время\n"
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


@bot.message_handler(commands=["set_doctor"])
@is_user_profile
def test_district_buttons(message: Message):
    if message.from_user is None:
        return
    user_id = message.from_user.id
    message_id = message.message_id
    chat_id = message.chat.id

    districts = Gorzdrav.get_districts()

    message_hash = keyboard_service.get_short_message_hash(
        message_id=message.message_id,
        chat_id=message.chat.id,
        user_id=user_id,
    )

    buttons = keyboard_service.get_districts_buttons(districts=districts)

    keyboard_service.save_buttons(
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        buttons=buttons,
    )

    kb = keyboard_service.get_keyboard_markup(
        message_hash=message_hash,
        page_number=0,
    )
    bot.send_message(
        chat_id=message.chat.id,
        text="Выберите район",
        reply_markup=kb,
    )
    SM.set_state(
        user_id=user_id,
        state_name=STATES_NAMES.SELECT_DISTRICT,
    )


@bot.callback_query_handler(func=lambda call: call.message and "/page/" in call.data)
def change_page(callback: CallbackQuery):
    """
    Функция для листания кнопок
    """
    if callback.data is None:
        return

    parts = callback.data.split("/")
    if len(parts) != 3:
        logger.error(f"{callback.data} have not 3 parts")
        return

    message_hash, _, page_number_str = parts
    page_number = int(page_number_str)

    new_kb = keyboard_service.get_keyboard_markup(
        message_hash=message_hash,
        page_number=page_number,
    )
    if new_kb is None:
        text = "Пожалуйста обновите запрос."
        bot.edit_message_text(
            text=text,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )
        return

    current_state_name: STATES_NAMES = SM.get_state(user_id=callback.from_user.id).name

    if current_state_name == STATES_NAMES.SELECT_LPU:
        back_button = InlineKeyboardButton(text="Назад", callback_data="lpu/back")
        new_kb.add(back_button)
    elif current_state_name == STATES_NAMES.SELECT_SPECIALTY:
        back_button = InlineKeyboardButton(text="Назад", callback_data="specialty/back")
        new_kb.add(back_button)
    elif current_state_name == STATES_NAMES.SELECT_DOCTOR:
        back_button = InlineKeyboardButton(text="Назад", callback_data="doctor/back")
        new_kb.add(back_button)

    bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=callback.message.text or "",
        reply_markup=new_kb,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("district/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_DISTRICT])
@handle_gorzdrav_exceptions
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

    buttons = keyboard_service.get_lpus_buttons(lpus)

    keyboard_service.save_buttons(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        user_id=call.from_user.id,
        buttons=buttons,
    )

    message_hash = keyboard_service.get_short_message_hash(
        message_id=call.message.message_id,
        chat_id=call.message.chat.id,
        user_id=call.from_user.id,
    )
    kb = keyboard_service.get_keyboard_markup(
        message_hash=message_hash,
        page_number=0,
    )
    if kb is None:
        logger.error("Keyboard markup is None")
        return
    kb.add(
        InlineKeyboardButton(
            text="Назад",
            callback_data="lpu/back",
        )
    )

    bot.send_message(
        chat_id=call.message.chat.id,
        text="Выберите медучреждение:",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("lpu/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_LPU])
@handle_gorzdrav_exceptions
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
    buttons: list[ButtonSchema] = keyboard_service.get_specialties_buttons(
        specialties=specialties
    )
    keyboard_service.save_buttons(
        user_id=call.from_user.id,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        buttons=buttons,
    )

    message_hash = keyboard_service.get_short_message_hash(
        user_id=call.from_user.id,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    kb = keyboard_service.get_keyboard_markup(
        message_hash=message_hash,
    )
    if kb is None:
        logger.error("Не удалось получить клавиатуру")
        return
    kb.add(
        InlineKeyboardButton(
            text="Назад",
            callback_data="specialty/back",
        )
    )

    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Выберите специальность в медучреждении {lpu.lpuFullName}:",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("specialty/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_SPECIALTY])
@handle_gorzdrav_exceptions
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

    buttons = keyboard_service.get_doctor_buttons(doctors)

    keyboard_service.save_buttons(
        user_id=call.from_user.id,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        buttons=buttons,
    )

    message_hash = keyboard_service.get_short_message_hash(
        user_id=call.from_user.id,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    kb = keyboard_service.get_keyboard_markup(
        message_hash=message_hash,
    )
    if kb is None:
        logger.error(f"Keyboard not found for message hash {message_hash}")
        return
    kb.add(InlineKeyboardButton(text="Назад", callback_data="doctor/back"))

    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Выберите врача в медучреждении {lpu.lpuFullName}:",
        reply_markup=kb,
    )

    state_payload["specialty_id"] = specialty_id
    SM.set_state(
        user_id=user_id,
        state_name=STATES_NAMES.SELECT_DOCTOR,
        payload=state_payload,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("doctor/"))  # type: ignore
@is_state(allowed_states_names=[STATES_NAMES.SELECT_DOCTOR])
@handle_gorzdrav_exceptions
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

    db_doctor = pydantic_models.DbDoctorToCreate(
        districtId=district_id,
        lpuId=lpu.id,
        specialtyId=specialty_id,
        doctorId=doctor_id,
    )
    doctor_id = DB.add_doctor(doctor=db_doctor)
    DB.add_user_doctor(user_id=user_id, doctor_id=doctor_id)

    SM.set_state(user_id=user_id, state_name=STATES_NAMES.HAVE_PROFILE)

    user = DB.get_user(user_id=user_id)
    if user is None:
        return
    ping_text = f"Отслеживание {'включено' if user.ping_status else 'отключено'}."

    link = Gorzdrav.generate_link(
        districtId=district_id,
        lpuId=lpu.id,
        specialtyId=specialty_id,
        scheduleId=doctor_id,
    )
    text = (
        f"Выбран врач {doctor.name}\n"
        + f"Свободных мест {doctor.freeParticipantCount}.\n"
        + f"Свободных талонов {doctor.freeTicketCount}.\n"
        + "\n"
        + f"{ping_text}\n\n"
    )
    text += f"Ссылка на запись: [ссылка]({link})"

    bot.send_message(
        chat_id=call.message.chat.id,
        text=text,
        parse_mode="markdown",
        disable_web_page_preview=True,
    )


@bot.message_handler(commands=["id"])  # type: ignore
def id_message(message: Message):
    """
    Пишет пользователю его telegram id.
    """
    bot.send_message(
        chat_id=message.chat.id, text="Ваш telegram id: " + str(message.chat.id)
    )


@bot.message_handler(commands=["on"])  # type: ignore
@is_user_profile
@is_user_have_doctor
def ping_on(message: Message):
    """
    Устанавливает статус проверки талонов для пользователя в True (Включена).
    """
    if message.from_user is None:
        return
    user_id: int = message.from_user.id
    # SyncOrm.update_user(user_id=user_id, ping_status=True)
    DB.set_user_ping_status(user_id=user_id, ping_status=True)
    user: DbUser | None = DB.get_user(user_id=user_id)
    if user is None:
        return
    text = f"Отслеживание {f'в пределах {user.limit_days} дней ' if user.limit_days else ''}включено"
    bot.reply_to(message=message, text=text)  # type: ignore


@bot.message_handler(commands=["off"])  # type: ignore
@is_user_profile
@is_user_have_doctor
def ping_off(message: Message):
    """
    Устанавливает статус проверки талонов для пользователя в False (Отключена).
    """
    if message.from_user is None:
        return
    user_id: int = message.from_user.id
    # SyncOrm.update_user(user_id=user_id, ping_status=False)
    DB.set_user_ping_status(user_id=user_id, ping_status=False)
    bot.reply_to(message=message, text="Отслеживание выключено")  # type: ignore


@bot.message_handler(commands=["delete"])  # type: ignore
@is_user_profile
def delete_user(message: Message):
    """
    Удаляет профиль пользователя из базы данных.
    """
    if message.from_user is None:
        return
    user_id = message.from_user.id

    DB.delete_user(user_id=user_id)
    SM.set_state(user_id=user_id, state_name=STATES_NAMES.NO_PROFILE)
    bot.reply_to(  # type: ignore
        message=message,
        text="Ваш профиль удалён.\n" + "Выполните команду /start за создания профиля.",
    )


@bot.message_handler(commands=["status"])  # type: ignore
@is_user_profile
@is_user_have_doctor
@handle_gorzdrav_exceptions
def get_status(message: Message):
    """
    Пишет пользователю информацию о его враче.
    """
    if message.from_user is None:
        return
    user_id: int = message.from_user.id
    user: DbUser | None = DB.get_user(user_id=user_id)
    if user is None:
        return
    user_doctor = DB.get_user_doctor(user_id=user_id)
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

    link: str = Gorzdrav.generate_link(
        districtId=user_doctor.districtId,
        lpuId=gorzdrav_doctor.lpuId,
        specialtyId=gorzdrav_doctor.specialtyId,
        scheduleId=gorzdrav_doctor.doctorId,
    )

    ping_text = f"Отслеживание {'включено' if user.ping_status else 'отключено'}."
    limit_days_text: str = f"Лимит дней: {
        user.limit_days if user.limit_days is not None else 'не установлен'
    }."
    text: str = f"{gorzdrav_doctor}\n{ping_text}\n{limit_days_text}"
    text += f"\n\nСсылка на запись: [ссылка]({link})"
    bot.reply_to(
        message=message,
        text=text,
        parse_mode="markdown",
        disable_web_page_preview=True,
    )


if __name__ == "__main__":
    logger.info("Bot start")
    logger.info("Bot username: " + str(bot.get_me().username))
    logger.info("Bot id: " + str(bot.get_me().id))
    logger.info("Bot first_name: " + bot.get_me().first_name)
    logger.info("Bot can_join_groups: " + str(bot.get_me().can_join_groups))
    logger.info(
        "Bot can_read_all_group_messages: "
        + str(bot.get_me().can_read_all_group_messages)
    )
    logger.info(
        "Bot supports_inline_queries: " + str(bot.get_me().supports_inline_queries)
    )
    logger.info("Bot started")

    # запускаем процесс с отправкой уведомлений
    old_scheduler = multiprocessing.Process(
        target=checker.old_scheduler,
        name="gorzdrav_checker",
        kwargs={"timeout_secs": Config.CHECKER_TIMEOUT_SECS},
        daemon=True,
    )
    old_scheduler.start()
    bot.polling(none_stop=True)
