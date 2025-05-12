import hashlib
import datetime
from pydantic import BaseModel
from pydantic import Field

from telebot.types import InlineKeyboardButton
from telebot.types import InlineKeyboardMarkup


class ButtonSchema(BaseModel):
    text: str
    callback_data: str


class CallbackPayload(BaseModel):
    user_id: int
    chat_id: int
    message_id: int
    buttons: list[ButtonSchema]
    live_time: datetime.timedelta = Field(default=datetime.timedelta(minutes=5))
    creation_time: int = Field(
        default_factory=lambda: int(datetime.datetime.now().timestamp()),
    )


class ButtonsService:
    def __init__(self):
        self.callbacks: dict[str, CallbackPayload] = dict()

    @staticmethod
    def message_hash(message_id: int, chat_id: int, user_id: int):
        return hashlib.sha256(
            f"{message_id}{chat_id}{user_id}".encode("utf-8"),
        ).hexdigest()

    def del_buttons(self, message_hash: str):
        """
        Удаляем кнопки из состояния
        """
        self.callbacks.pop(message_hash, None)

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
        msg_hash = self.message_hash(message_id, chat_id, user_id)
        payload = CallbackPayload(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            buttons=buttons,
        )
        self.callbacks[msg_hash] = payload

    def __get_payload(
        self,
        message_id: int,
        chat_id: int,
        user_id: int,
    ):
        """
        Получаем содержание для кнопок из состояния
        """
        msg_hash = self.message_hash(message_id, chat_id, user_id)
        payload = self.callbacks.get(msg_hash)
        return payload

    def __get_buttons(self, message_hash: str, page_number: int = 0):
        """
        Получаем кнопки для сообщения
        """
        payload = self.callbacks.get(message_hash)
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
        Возвращает клавиатуру
        """
        page_size: int = 10
        buttons = self.__get_buttons(message_hash=message_hash)
        if buttons is None:
            return None

        page_buttons = self.__get_page_buttons(
            buttons=buttons,
            page_number=page_number,
            page_size=page_size,
        )
        if page_buttons is None:
            return None
        kb = InlineKeyboardMarkup()
        for button in page_buttons:
            kb_button = InlineKeyboardButton(
                text=button.text,
                callback_data=button.callback_data,
            )
            kb.add(kb_button)

        if len(page_buttons) <= page_size:
            return kb

        # добавляем кнопки перехода
        prev_page_number = page_number - 1
        next_page_number = page_number + 1

        prev_page_callback_data = f"{message_hash}_page_{prev_page_number}"
        next_page_callback_data = f"{message_hash}_page_{next_page_number}"

        prev_button = InlineKeyboardButton(
            text=f"[{prev_page_number}] <<",
            callback_data=prev_page_callback_data,
        )
        next_button = InlineKeyboardButton(
            text=f"[{next_page_number}] >>",
            callback_data=next_page_callback_data,
        )
        row_buttons: list[InlineKeyboardButton] = []
        if prev_page_number >= 0:
            row_buttons.append(prev_button)

        total_pages = self.get_total_pages_number(
            n_buttons=len(buttons),
            page_size=page_size,
        )
        if next_page_number < total_pages:
            row_buttons.append(next_button)

        kb.row(*row_buttons)
        return kb

    @staticmethod
    def get_total_pages_number(n_buttons: int, page_size: int):
        """
        Общее количество страниц
        """
        full_pages = n_buttons // page_size
        partial_pages = int(n_buttons % page_size > 0)

        return full_pages + partial_pages
