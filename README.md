# Проект бота для проверки талонов к врачу в через апи в горздраве

## Желаемый функционал
Бот должен проверять периодически достпновть талончиков к врачу и выводить оповещение в телеграм, если у врача есть свободные талончики

## Функуионал
- хранить для каждого пользователя бота настройки
- согласно настройкам каждого пользователя проверять врачей
- выводить пользователям бота свободные талончики
- выводить список врачей для которых ведется поиск
- добавлять и удалять врачей

## Команды бота
/status - немедленный статус врача
/on - включить отслеживание свободных мест для записи
/off - отключить отслеживание свободных мест для записи
/help - помощь


## Пинговалка
Это отдельный процесс, который проверяет доступность врачей из бд и записывает их статус в бд

## БД

- должна хранить настройки каждого пользователя:
    - настройки для поиска
    - включен ли поиск

- сущности для поиска - это врач в поликлинике по специальности

## API
- https://gorzdrav.spb.ru/_api/api/v2/shared/districts - список районов
- https://gorzdrav.spb.ru/_api/api/v2/shared/district/10/lpus - список медучереждений в 10 районе
- https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/229/specialties - информация по всем свободным специальностям в больнице с ид 229
- https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/speciality/981/doctors - информация по доступным врачам в больнице 30 по специальности 981
- https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1138/doctor/36/timetable - расписание врача 36 в больнице 1138
- https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/30/doctor/222618/appointments - доступные назначения к врачу
    
### Github API

https://github.com/egorantonov/gorzdrav/wiki/SPB-Gorzdrav-API-Documentation


# Сделать
- бот должен выдавать ссылку на врача, как только у него появятся талончики
    для этого надо узнать в каком районе он находится. Просмотреть все районы - составить список медицинских учреждений и найти то, в котором он есть. Можно закешировать выхов функции получения списка районов и списка медицинских учреждений в каждом районе.
- оптимизация. 
    - Каждый доктор может оказаться в одной и той же поликлинике. Можно кешировать запросы к спискам докторов `.get_doctors(hospital_id, speciality_id, time_minutes)` в пределах нескольких минут, чтобы не делать несколько запросов к одной и той же поликлинике. Если указывать текущее время в минутах, то будет работать функция `lru_cache`.
    - можно (нужно) кешировать список районов и список поликлиник в районах, чтобы не делать повторных запросов. Предположим можно делать это раз в день.