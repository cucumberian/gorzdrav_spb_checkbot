# Бот для телеграм для проверки талонов к врачу через апи горздрава.

## Установка и запуск

### Конфигурация программы

Настройки для запуска программы хранятся в текстовом файле `.env`.

Параметр | Описание
-- | --
`BOT_TOKEN` | токен телеграм бота от `@BotFather`
`DB_FILE` | имя файла базы данных (создается новый если файла нет)
`CHECKER_TIMEOUT_SECS` | период проверки свободных талончиков через api горздрава

### Запуск

Установите настройки в файле `config.py` или в системных переменных.
Затем установите необходимые зависимости из файла `requirements.txt` и запустите `app.py` через интерпретатор Python:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

## Функционал

Бот проверяет периодически доступность талончиков к врачу и выводит оповещение в телеграм пользователю, если у врача есть свободные талончики.

## Команды бота

Команда       | Описание
-|-
`/status`     | показать статус врача и статус отслеживания
`/on`         | включить отслеживание свободных мест для записи
`/off`        | отключить отслеживание свободных мест для записи
`/help`       | помощь
`/start`      | создать профиль пользователя бота
`/delete`     | удалить профиль пользователя бота
`/set_doctor` | задать врача для отслеживания

## База данных

- хранит пользователей бота:
  - телеграм ид
  - включен ли мониторинг свободных мест у врача
  - ссылка на врача
- хранит врачей пользователя:
  - ид района
  - ид медучреждения
  - ид специальности
  - ид врача

## API

- [https://gorzdrav.spb.ru/_api/api/v2/shared/districts](https://gorzdrav.spb.ru/_api/api/v2/shared/districts) - список районов
- [https://gorzdrav.spb.ru/_api/api/v2/shared/district/10/lpus](https://gorzdrav.spb.ru/_api/api/v2/shared/district/10/lpus) - список медучреждений в 10 районе
- [https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/229/specialties](https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/229/specialties) - информация по всем свободным специальностям в больнице с ид 229
- [https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/speciality/981/doctors](https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/speciality/981/doctors) - информация по доступным врачам в больнице 30 по специальности 981
- [https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1138/doctor/36/timetable](https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1138/doctor/36/timetable) - расписание врача 36 в больнице 1138
- [https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/doctor/222618/appointments](https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/doctor/222618/appointments) - доступные назначения к врачу

## Gorzdrav API

[https://github.com/egorantonov/gorzdrav/wiki/SPB-Gorzdrav-API-Documentation](https://github.com/egorantonov/gorzdrav/wiki/SPB-Gorzdrav-API-Documentation)
