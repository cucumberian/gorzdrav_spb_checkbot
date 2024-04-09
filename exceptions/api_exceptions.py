class GorzdravExceptionBase(Exception):
    """
    {
    "success": false,
    "errorCode": 645,
    "message": "Не найдено расписание медицинского ресурса",
    "requestId": "00000000-0000-0000-0000-000000000000"
    },
    
    {'errorCode': 660,
    'message': 'Что-то пошло не так. Попробуйте записаться позже',
    'requestId': '00000000-0000-0000-0000-000000000000',
    'success': False}

    {'errorCode': 37,
    'message': 'Отсутствуют специальности для записи на приём. Для записи к врачу '
                'обратитесь в регистратуру или колл-центр медицинской организации',
    'requestId': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
    'success': False}
    
    {'errorCode': 602,
    'message'='Медорганизация нам не ответила. Попробуйте записаться позже или'
                ' обратитесь в регистратуру медорганизации',
    'success': False}
    """

    def __init__(
        self,
        message: str | None = None,
        errorCode: int | None = None,
        url: str | None = None,
    ):
        super().__init__(self)
        self.message = message
        self.errorCode = errorCode
        self.url = url

    def to_dict(self):
        return dict(
            message=self.message, errorCode=self.errorCode, url=self.url
        )

    def __str__(self):
        return f"message={self.message}, errorCode={self.errorCode}, url={self.url}"


class NoDoctorsException(GorzdravExceptionBase):
    default_message = "Отсутствуют специалисты для приёма \
        по выбранной специальности. \
        Обратитесь в регистратуру медорганизации"
    default_errorCode = 38

    def __init__(
        self,
        message: str | None = default_message,
        url: str | None = None,
    ):
        super().__init__(
            message=message,
            errorCode=self.__class__.default_errorCode,
            url=url,
        )


class NoTicketsException(GorzdravExceptionBase):
    default_message = "Отсутствуют свободные талоны. \
        Попробуйте записаться позже или обратитесь \
        в регистратуру медорганизации"
    default_errorCode = 39

    def __init__(
        self,
        message: str | None = default_message,
        url: str | None = None,
    ):
        super().__init__(
            message=message,
            errorCode=self.__class__.default_errorCode,
            url=url,
        )


class NoSpecialtiesException(GorzdravExceptionBase):
    default_message = "Отсутствуют специальности для записи на приём. \
        Для записи к врачу обратитесь в регистратуру или колл-центр \
        медицинской организации"
    default_errorCode = 39

    def __init__(
        self,
        message: str | None = default_message,
        url: str | None = None,
    ):
        super().__init__(
            message=message,
            errorCode=self.__class__.default_errorCode,
            url=url,
        )


class Api616Exception(GorzdravExceptionBase):
    default_message = "Возникла ошибка в работе \
    медицинской информационной системы медицинской \
    организации. Попробуйте позже или обратитесь в \
    регистратуру медицинской организации."
    default_errorCode = 616

    def __init__(
        self,
        message: str = default_message,
        url: str | None = None,
    ):
        super().__init__(
            message=message,
            errorCode=self.__class__.default_errorCode,
            url=url,
        )


class Api603Exception(GorzdravExceptionBase):
    default_message = "Время ожидания ответа от медицинской организации \
        истекло. Попробуйте записаться позже или обратитесь в регистратуру \
        медицинской организации."
    default_errorCode = 603

    def __init__(
        self,
        message: str = default_message,
        url: str | None = None,
    ):
        super().__init__(
            message=message,
            errorCode=self.__class__.default_errorCode,
            url=url,
        )


class GorzdravException(GorzdravExceptionBase):
    def __init__(
        self,
        message: str,
        errorCode: int,
        url: str | None = None,
    ):
        super().__init__(message=message, errorCode=errorCode, url=url)
        match errorCode:
            case 37:
                raise NoSpecialtiesException(message=message, url=url)
            case 38:
                raise NoDoctorsException(message=message, url=url)
            case 39:
                raise NoTicketsException(message=message, url=url)
            case 616:
                raise Api616Exception(message=message, url=url)
            case 603:
                raise Api603Exception(message=message, url=url)
            case _:
                raise GorzdravExceptionBase(
                    message=message,
                    errorCode=errorCode,
                    url=url,
                )
