import datetime
import sqlite3
import hashlib

from .models import Doctor
from .models import DoctorToCreate
from .models import User
from config import Config

class SqliteDb:
    """
    Класс для работы с БД
    params: file: название файла с базой данных
    type: file: str
    """

    @staticmethod
    def get_doctor_hash(doctor: DoctorToCreate) -> str:
        """
        Генерация хеша доктора
        params: doctor: Doctor
        type: doctor: Doctor
        return: hash: str
        """
        hashed_string = (
            doctor.doctor_id + doctor.speciality_id + doctor.hospital_id
        )
        return hashlib.shake_128(hashed_string.encode()).hexdigest(10)

    def __init__(self, file: str = Config.db_file) -> None:
        self.file = file
        self.connection = sqlite3.connect(
            database=self.file, check_same_thread=False, timeout=5
        )
        self.cursor = self.connection.cursor()
        self.create_db()

    def create_db(self) -> None:
        """
        Создаются таблицы докторов для поиска
        и пользователей телеграм бота
        """
        self.create_table_doctors()
        self.create_table_users()

    def create_table_users(self) -> None:
        """
        Создание таблицы doctors:
        id - идентификатор доктора
        doctor_id - идентификатор доктора в горздраве
        speciality_id - идентификатор специальности
        hospital_id - идентификатор организации
        ping_status - флаг активности проверки
        last_seen - дата последнего входа в бота
        для каждого доктора может быть только один юзер, который его наблюдает
        """
        q = """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            ping_status INTEGER DEFAULT 0,
            doctor_id VARCHAR(40),
            last_seen DATETIME,
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        );"""
        self.cursor.execute(q)
        self.connection.commit()

    def create_table_doctors(self) -> None:
        """
        Создание таблицы doctors:
        id - идентификатор доктора
        doctor_id - идентификатор доктора в горздраве
        speciality_id - идентификатор специальности доктора
        hospital_id - идентификатор организации
        """
        q = """CREATE TABLE IF NOT EXISTS doctors (
            id VARCHAR(40) PRIMARY KEY,
            doctor_id TEXT REQUIRED,
            speciality_id TEXT REQUIRED,
            hospital_id TEXT REQUIRED
        );"""
        self.cursor.execute(q)
        self.connection.commit()

    def add_user(self, user: User) -> None:
        """
        Добавление пользователя в базу данных
        params: user: пользователь в telegram
        type: user: models.User
        return: None
        """
        q = """
        INSERT OR IGNORE INTO USERS
        (id, ping_status, doctor_id, last_seen)
        values (?, ?, ?, ?)
        """
        self.cursor.execute(
            q, (user.id, user.ping_status, user.doctor_id, user.last_seen)
        )
        self.connection.commit()

    def get_user(self, user_id: int) -> User | None:
        if not isinstance(user_id, int):
            raise TypeError("user_id must be int")
        q = """
        SELECT
            id,
            ping_status,
            doctor_id,
            last_seen
        FROM users WHERE id = ?"""
        result = self.cursor.execute(q, (user_id,)).fetchone()
        if result is None:
            return None
        (id, ping_status, doctor_id, last_seen) = result
        timestamp = datetime.datetime.fromisoformat(last_seen)
        return User(
            id=id,
            ping_status=ping_status,
            doctor_id=doctor_id,
            last_seen=timestamp,
        )

    def add_doctor(self, doctor: DoctorToCreate) -> str:
        """
        Добавление доктора в базу данных
        params: doctor: доктор
        type: doctor: models.DoctorToCreate
        return: str: id доктора
        """
        q = """
        INSERT OR IGNORE INTO doctors
        (id, doctor_id, speciality_id, hospital_id)
        values (?, ?, ?, ?)
        """
        id = self.__class__.get_doctor_hash(doctor)
        self.cursor.execute(
            q, (id, doctor.doctor_id, doctor.speciality_id, doctor.hospital_id)
        )
        self.connection.commit()
        return id

    def get_doctor(self, doctor_id: str) -> Doctor | None:
        """
        Получение доктора из базы данных
        params: doctor_id: id доктора
        type: doctor_id: str
        return: Doctor | None
        """
        q = """
        SELECT
            id,
            doctor_id,
            speciality_id,
            hospital_id
        FROM doctors
        WHERE doctors.id = ?;
        """
        self.cursor.execute(q, (doctor_id,))
        result = self.cursor.fetchone()
        if result is None:
            return None
        (id, doctor_id, speciality_id, hospital_id) = result
        return Doctor(
            id=id,
            doctor_id=doctor_id,
            speciality_id=speciality_id,
            hospital_id=hospital_id,
        )

    def get_user_ping_status(self, user_id: int) -> bool:
        q = """
        SELECT
            users.ping_status
        FROM users
        WHERE users.id = ?;
        """
        self.cursor.execute(q, (user_id,))
        result = self.cursor.fetchone()[0]
        return bool(result)

    def set_user_ping_status(
        self, user_id: int, ping_status: bool = False
    ) -> None:
        q = """
        UPDATE users
            set ping_status = ?
            WHERE users.id = ?;
        """
        self.cursor.execute(q, (ping_status, user_id))
        self.connection.commit()

    def set_user_ping(self, user_id: int) -> None:
        self.set_user_ping_status(user_id=user_id, ping_status=True)

    def clear_user_ping(self, user_id: int) -> None:
        self.set_user_ping_status(user_id, 0)

    def add_user_doctor(self, user_id: int, doctor_id: str) -> None:
        q = """ UPDATE users set doctor_id = ? where id = ?;"""
        self.cursor.execute(q, (doctor_id, user_id))
        self.connection.commit()

    def get_user_doctor(self, user_id: int) -> DoctorToCreate | None:
        """
        Возвращает доктора пользователя или None, если доктора нет.
        params: user_id: id пользователя
        type: user_id: int
        return: Doctor | None
        """
        q = """
        SELECT
            doctors.id,
            doctors.doctor_id,
            doctors.speciality_id,
            doctors.hospital_id
        FROM doctors
        WHERE
                doctors.id == (SELECT doctor_id FROM users WHERE id == ?)
        ;
        """
        self.cursor.execute(q, (user_id,))
        result = self.cursor.fetchone()
        if result is None:
            return None
        (id, doctor_id, speciality_id, hospital_id) = result
        doctor = Doctor(
            id=id,
            doctor_id=doctor_id,
            speciality_id=speciality_id,
            hospital_id=hospital_id,
        )
        return doctor

    def del_user(self, user_id: int) -> None:
        q = """ DELETE FROM users WHERE id = ?"""
        self.cursor.execute(q, (user_id,))
        self.connection.commit()

    def update_user_time(
        self, user_id: int, timestamp=datetime.datetime.now()
    ):
        q = """ UPDATE users SET last_seen = ? WHERE id = ?;"""
        self.cursor.execute(
            q,
            (
                timestamp,
                user_id,
            ),
        )
        self.connection.commit()

    def get_active_doctors(self) -> list[Doctor]:
        """
        Вернет список докторов, которыми интересуются пользователи
        """
        q = """
        SELECT
            doctors.id,
            doctors.doctor_id,
            doctors.speciality_id,
            doctors.hospital_id
        FROM doctors
        WHERE doctors.id IN (
            SELECT users.doctor_id FROM users WHERE ping_status == 1
        );
        """
        self.cursor.execute(q)
        results = self.cursor.fetchall()
        doctors: list[Doctor] = [
            Doctor(
                id=d[0], doctor_id=d[1], speciality_id=d[2], hospital_id=d[3]
            )
            for d in results
        ]
        return doctors

    def get_users_by_doctor(self, doctor_id: str) -> list[User]:
        q = """
            SELECT
                users.id,
                users.ping_status,
                users.doctor_id,
                users.last_seen
            FROM users
            WHERE users.doctor_id == ?;
        """
        self.cursor.execute(q, (doctor_id,))
        results = self.cursor.fetchall()
        users = [
            User(id=d[0], ping_status=d[1], doctor_id=d[2], last_seen=d[3])
            for d in results
        ]
        return users
