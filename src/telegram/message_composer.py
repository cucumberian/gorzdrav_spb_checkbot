class TgMessageComposer:
    @staticmethod
    def get_doc_ready_message_md(
        doctor_name: str,
        free_participant_count: int,
        free_ticket_count: int,
        doctor_link: str,
    ) -> str:
        message = (
            f"Врач {doctor_name} доступен для записи.\n"
            + f"Мест для записи: {free_participant_count}.\n"
            + f"Талонов для записи: {free_ticket_count}.\n"
            + "\n"
            + f"Запишитесь на приём по [ссылке]({doctor_link})\n\n"
            + "Отслеживание отключено."
        )
        return message

    @staticmethod
    def get_doc_selected_message_md(
        doctor_name: str,
        free_participant_count: int,
        free_ticket_count: int,
        doctor_link: str,
        ping_status: bool,
    ) -> str:
        ping_text = f"Отслеживание {'включено' if ping_status else 'отключено'}."
        text = (
        f"Выбран врач {doctor_name}\n"
        + f"Свободных мест {free_participant_count}.\n"
        + f"Свободных талонов {free_ticket_count}.\n"
        + "\n"
        + f"{ping_text}\n\n"
    )
        text += f"Ссылка на запись: [ссылка]({doctor_link})"
        return text