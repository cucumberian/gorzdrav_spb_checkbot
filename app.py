import telebot
import requests
import time
import modules.validate
import modules.net
import modules.db

import multiprocessing

from config import Config


print(Config.bot_token)

bot = telebot.TeleBot(Config.bot_token)

gorzdrav = modules.net.GorzdravSpbAPI()

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    db = modules.db.SqliteDb(file=Config.db_file)
    # удаляем и создаем пользователя заного
    db.del_user(user_id)
    db.add_user(user_id)
    bot.reply_to(message, 'Ваш профиль создан.')

@bot.message_handler(commands=['help'])
def get_help(message):
    text = """/start - старт
/status - узнать текущий статус талонов у врача
/on - включить отслеживание
/off - отключить отслеживание

Пришлите боту ссылку с горздрава на врача, чтобы его наблюдать.
    """
    bot.reply_to(message, text)


@bot.message_handler(commands=['id'])
def id_message(message):
    bot.send_message(message.chat.id, 'Ваш id: ' + str(message.chat.id))

@bot.message_handler(commands=['on'])
def ping_on(message):
    user_id = message.from_user.id
    db = modules.db.SqliteDb(file=Config.db_file)
    db.set_user_ping(user_id)
    bot.reply_to(message, 'Проверка включена')

@bot.message_handler(commands=['off'])
def ping_off(message):
    user_id = message.from_user.id
    db = modules.db.SqliteDb(file=Config.db_file)
    db.clear_user_ping(user_id)
    bot.reply_to(message, 'Проверка выключена')

@bot.message_handler(commands=['status'])
def get_status(message):
    user_id = message.from_user.id
    db = modules.db.SqliteDb(file=Config.db_file)
    doctor_params = db.get_user_doctor(user_id)
    if not doctor_params:
        bot.reply_to(message, 'Вы еще не добавили врача\nПришлите боту ссылку с сайта https://gorzdrav.spb.ru/ с врачем.')
        return
    else:
        # bot.reply_to(message, json.dumps(doctor_params, indent=4))
        doctor_id = doctor_params.get('doctor_id') 
        speciality_id = doctor_params.get('speciality_id') 
        hospital_id = doctor_params.get('hospital_id')

        if (doctor_id and speciality_id and hospital_id):
            doctor = gorzdrav.get_doctor(
                doctor_id=doctor_id, 
                speciality_id=speciality_id, 
                hospital_id=hospital_id
            )
            if doctor:
                print(doctor.info)
                checked = db.get_user_ping_status(user_id=user_id)
                text = f"{doctor}\nСтатус проверки: {'Вкл' if checked else 'Откл'}"
                bot.reply_to(message, text)
            else:
                bot.reply_to(message, 'Врач не найден')
    

@bot.message_handler(
        func=lambda i: modules.validate.is_domain(i.text) or modules.validate.is_url(i.text), content_types=['text']
)
def get_text_messages(message):
    text = message.text
    # bot.reply_to(message, "url detected\n"+text)
    parse_result = gorzdrav.url_parse(text)
    user_id = message.from_user.id
    db = modules.db.SqliteDb(file=Config.db_file)
    db.update_user_time(user_id)
    if parse_result:
        # bot.reply_to(message, json.dumps(parse_result, indent=4))
        doc_id = db.add_doctor(**parse_result)
        db.add_user_doctor(user_id, doctor_id=doc_id)
        doctor_ids = db.get_user_doctor(user_id)
        doctor = gorzdrav.get_doctor(
            doctor_id=doctor_ids.get('doctor_id'), 
            speciality_id=doctor_ids.get('speciality_id'), 
            hospital_id=doctor_ids.get('hospital_id')
        )
        bot.reply_to(message, f"к вам добавлен врач: {doctor}")
    else:
        bot.reply_to(message, "не удалось получить данные из ссылки")


# send message to telegram with requests.post

def send_message(message, api_token: str, chat_id):
    url = f'https://api.telegram.org/bot{api_token}/sendMessage'
    data = {'chat_id': chat_id, 'text': message}
    requests.post(url, data=data)


def checker(bot_token,  db_file, timeout_secs=60):
    print("checker process started")
    gorzdrav = modules.net.GorzdravSpbAPI()
    db = modules.db.SqliteDb(file=db_file)

    while True:
        doctors_dicts = db.get_active_doctors()
        for d in doctors_dicts:
            doc = gorzdrav.get_doctor(**d)
            if doc.is_free:
                doc_db_id = f"{doc.hospital_id}_{doc.speciality_id}_{doc.id}"
                doc_users = db.get_users_by_doctor(doc_db_id)
                print(f"{doc_users = }")
                text = f"{doc}"
                for u in doc_users:
                    send_message(message=text, api_token=bot_token, chat_id = u)
                    time.sleep(0.1)
        
        time.sleep(timeout_secs)

        


if __name__ == "__main__":
    print("Bot start")
    print("Bot username: " + str(bot.get_me().username))
    print("Bot id: " + str(bot.get_me().id))
    print("Bot first_name: " + bot.get_me().first_name)
    print("Bot can_join_groups: " + str(bot.get_me().can_join_groups))
    print("Bot can_read_all_group_messages: " + str(bot.get_me().can_read_all_group_messages))
    print("Bot supports_inline_queries: " + str(bot.get_me().supports_inline_queries))
    print("Bot started")

    checker = multiprocessing.Process(
        target=checker, 
        name='gorzdrav_checker', 
        kwargs={
            'bot_token': Config.bot_token, 
            'timeout_secs': Config.checker_timeout_secs,
            'db_file': Config.db_file,
        },
        daemon=True,
    )
    checker.start()

    bot.polling(none_stop=True)