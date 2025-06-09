import hashlib
import datetime
from pydantic import BaseModel
from pydantic import Field

from telebot.types import InlineKeyboardButton
from telebot.types import InlineKeyboardMarkup

from gorzdrav.models import ApiDistrict, ApiDoctor, ApiLPU, ApiSpecialty


class ButtonSchema(BaseModel):
    text: str
    callback_data: str


class CallbackPayloadSchema(BaseModel):
    user_id: int
    chat_id: int
    message_id: int
    buttons: list[ButtonSchema]
    live_time: datetime.timedelta = Field(default=datetime.timedelta(minutes=5))
    creation_time: int = Field(
        default_factory=lambda: int(datetime.datetime.now().timestamp()),
    )


class KeyboardService:
    def __init__(self, page_size: int = 10):
        self.page_size = page_size
        self.storage: dict[str, CallbackPayloadSchema] = dict()

    @staticmethod
    def get_message_hash(message_id: int, chat_id: int, user_id: int):
        """Хэш сообщения"""
        return hashlib.sha256(
            f"{message_id}{chat_id}{user_id}".encode("utf-8"),
        ).hexdigest()

    @classmethod
    def get_short_message_hash(cls, message_id: int, chat_id: int, user_id: int):
        """Обрезанный хэш сообщения, чтобы влезть в длину колбека телеграмма"""
        return cls.get_message_hash(message_id, chat_id, user_id)[:12]

    def del_buttons(self, message_hash: str):
        """
        Удаляем кнопки из состояния
        """
        self.storage.pop(message_hash, None)

    def save_buttons(
        self,
        message_id: int,
        chat_id: int,
        user_id: int,
        buttons: list[ButtonSchema],
    ):
        """
        Сохраняем кнопки в состояние
        """
        msg_hash = self.get_short_message_hash(
            message_id,
            chat_id,
            user_id,
        )
        payload = CallbackPayloadSchema(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            buttons=buttons,
        )
        self.storage[msg_hash] = payload

    def __get_payload(self, message_id: int, chat_id: int, user_id: int):
        """
        Получаем содержание для кнопок из состояния
        """
        msg_hash = self.get_short_message_hash(message_id, chat_id, user_id)
        payload = self.storage.get(msg_hash)
        return payload

    def __get_buttons_from_storage(self, message_hash: str, page_number: int = 0):
        """
        Получаем кнопки для сообщения
        """
        payload = self.storage.get(message_hash)
        if payload is None:
            return None

        buttons = payload.buttons
        return buttons

    def __get_page_buttons(
        self, buttons: list[ButtonSchema], page_number: int, page_size: int
    ):
        """
        Список кнопок на конкретной странице
        """
        start_index = page_number * page_size
        end_index = start_index + page_size
        page_buttons = buttons[start_index:end_index]

        return page_buttons

    def get_keyboard_markup(self, message_hash: str, page_number: int = 0):
        """
        Возвращает клавиатуру по хэшу сообщения
        """

        kb = InlineKeyboardMarkup()
        buttons = self.__get_buttons_from_storage(message_hash=message_hash)
        if buttons is None:
            return None

        page_buttons = self.__get_page_buttons(
            buttons=buttons,
            page_number=page_number,
            page_size=self.page_size,
        )
        if page_buttons is None:
            return None

        for button in page_buttons:
            kb_button = InlineKeyboardButton(
                text=button.text,
                callback_data=button.callback_data,
            )
            kb.add(kb_button)

        total_pages = self.get_total_pages_number(
            n_buttons=len(buttons),
            page_size=self.page_size,
        )

        if total_pages <= 1:
            print(f"total_pages <= 1: {total_pages} <=1 ")
            return kb

        # добавляем кнопки перехода
        empty_button = InlineKeyboardButton(text=" ", callback_data="empty")
        nav_buttons = [empty_button, empty_button]

        prev_page_number = page_number - 1
        next_page_number = page_number + 1

        prev_page_callback_data = f"{message_hash}/page/{prev_page_number}"
        next_page_callback_data = f"{message_hash}/page/{next_page_number}"

        prev_button = InlineKeyboardButton(
            text=f"< стр {prev_page_number + 1}",
            callback_data=prev_page_callback_data,
        )
        next_button = InlineKeyboardButton(
            text=f"стр {next_page_number + 1} >",
            callback_data=next_page_callback_data,
        )

        if prev_page_number >= 0:
            nav_buttons[0] = prev_button

        if next_page_number < total_pages:
            nav_buttons[1] = next_button

        kb.row(*nav_buttons)
        return kb

    @staticmethod
    def get_total_pages_number(n_buttons: int, page_size: int):
        """
        Общее количество страниц
        """
        full_pages = n_buttons // page_size
        partial_pages = int(n_buttons % page_size > 0)

        return full_pages + partial_pages

    def get_keyboard_from_buttons(
        self,
        message_hash: str,
        buttons: list[ButtonSchema],
        page_number: int = 0,
        page_size: int = 10,
    ):
        """Возвращает готовую клавиатура для кнопок с навигацией."""
        kb = InlineKeyboardMarkup()
        total_pages = self.get_total_pages_number(
            n_buttons=len(buttons),
            page_size=page_size,
        )
        print(f"{total_pages = }")
        if total_pages <= 1:
            for button in buttons:
                inline_button = InlineKeyboardButton(
                    text=button.text,
                    callback_data=button.callback_data,
                )
                kb.add(inline_button)
        return kb

    @staticmethod
    def __get_button_text(text: str, max_len: int = 50):
        """Обрезает текст кнопки до максимальной длины."""
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    @staticmethod
    def __get_district_callback(district_id: str):
        """Возвращает callback для района."""
        return f"district/{district_id}"

    @classmethod
    def get_districts_buttons(cls, districts: list[ApiDistrict]):
        buttons: list[ButtonSchema] = []
        for district in districts:
            button_text = cls.__get_button_text(district.name)
            button_callback = cls.__get_district_callback(district.id)
            button = ButtonSchema(
                text=button_text,
                callback_data=button_callback,
            )
            buttons.append(button)

        return buttons

    @staticmethod
    def get_shorten_lpu_name(lpu_name: str):
        """Возвращает сокращенное название ЛПУ."""
        to_remove = ["СПб", "ГБУЗ", "Городская", "Санкт-Петербург"]
        for item in to_remove:
            lpu_name = lpu_name.replace(item, "")
        return lpu_name.strip()

    @classmethod
    def get_lpus_buttons(cls, lpus: list[ApiLPU]):
        buttons: list[ButtonSchema] = []
        for lpu in lpus:
            short_lpu_name = cls.get_shorten_lpu_name(lpu.lpuFullName or "нет имени")
            button_text = cls.__get_button_text(f"{short_lpu_name} - {lpu.address}")
            button_callback = f"lpu/{lpu.id}"
            button = ButtonSchema(
                text=button_text,
                callback_data=button_callback,
            )
            buttons.append(button)
        return buttons

    @classmethod
    def get_specialties_buttons(cls, specialties: list[ApiSpecialty]):
        buttons: list[ButtonSchema] = []
        for specialty in specialties:
            button_text = cls.__get_button_text(specialty.name or "нет специальности")
            button_callback = f"specialty/{specialty.id}"
            button = ButtonSchema(
                text=button_text,
                callback_data=button_callback,
            )
            buttons.append(button)
        return buttons

    @classmethod
    def get_doctor_buttons(cls, doctors: list[ApiDoctor]):
        buttons: list[ButtonSchema] = []
        for doc in doctors:
            button_text = cls.__get_button_text(
                f"[{doc.freeParticipantCount}:{doc.freeTicketCount}] {doc.name}"
            )
            button_callback = f"doctor/{doc.id}"
            button = ButtonSchema(
                text=button_text,
                callback_data=button_callback,
            )
            buttons.append(button)
        return buttons
