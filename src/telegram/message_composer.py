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
