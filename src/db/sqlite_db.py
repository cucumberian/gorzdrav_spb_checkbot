import datetime
import hashlib
import sqlite3

from models.pydantic_models import DbDoctor
from models.pydantic_models import DbDoctorToCreate
from models.pydantic_models import DbUser


class SqliteDb:
    """
    Класс для работы с БД
    params: file: название файла с базой данных
    type: file: str
    """

    @staticmethod
    def get_doctor_hash(doctor: DbDoctorToCreate) -> str:
        """
        Генерация хеша доктора
        Args:
            doctor (DbDoctorToCreate): объект доктора
        Returns:
            str: хеш доктора для хранения в БД
        """
        hashed_string = f"{doctor.doctorId}_{doctor.specialtyId}_{doctor.lpuId}"
        return hashlib.shake_128(hashed_string.encode()).hexdigest(10)

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = sqlite3.connect(
            database=self.db_path, check_same_thread=False, timeout=5
        )
        self.cursor = self.connection.cursor()
        self.create_db()

    def create_db(self):
        """
        Создаются таблицы докторов для поиска
        и пользователей телеграм бота
        """
        self.create_table_doctors()
        self.create_table_users()

    def create_table_users(self):
        """
        Создание таблицы users:
        id:int - идентификатор пользователя в telegram
        doctor_id:str - идентификатор доктора, к которому относится пользователь
        ping_status: bool - флаг активности проверки
        last_seen:datetime - дата последнего входа в бота
        Для каждого доктора может быть только один юзер, который его наблюдает
        """
        q = """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            ping_status INTEGER DEFAULT 0 NOT NULL,
            doctor_id VARCHAR(40),
            last_seen DATETIME,
            limit_days INTEGER,
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        );"""
        self.cursor.execute(q)
        self.connection.commit()

    def create_table_doctors(self) -> None:
        """
        Создание таблицы doctors:
        id: str - идентификатор доктора
        districtId: str - идентификатор района
        lpuId:int - идентификатор медучреждения
        specialtyId:str - идентификатор специальности доктора
        doctorId:str - идентификатор доктора в горздраве
        """
        q = """CREATE TABLE IF NOT EXISTS doctors (
            id VARCHAR(40) PRIMARY KEY,
            districtId TEXT REQUIRED,
            lpuId INT REQUIRED,
            specialtyId TEXT REQUIRED,
            doctorId TEXT REQUIRED
        );"""
        self.cursor.execute(q)
        self.connection.commit()

    def add_user(self, user: DbUser) -> None:
        """
        Добавление пользователя в базу данных
        Args:
            user (DbUser): объект пользователя
        Returns:
            None: None
        """
        q = """
        INSERT OR IGNORE INTO USERS
        (id, ping_status, doctor_id, last_seen, limit_days)
        values (?, ?, ?, ?, ?)
        """
        if user.last_seen is None:
            user.last_seen = datetime.datetime.now(datetime.UTC)
        if user.ping_status is None:
            user.ping_status = False
        self.cursor.execute(
            q,
            (
                user.id,
                user.ping_status,
                user.doctor_id,
                user.last_seen,
                user.limit_days,
            ),
        )
        self.connection.commit()

    def get_user(self, user_id: int) -> DbUser | None:
        if not isinstance(user_id, int):
            raise TypeError("user_id must be int")
        q = """
        SELECT
            id,
            ping_status,
            doctor_id,
            last_seen,
            limit_days
        FROM users WHERE id = ?"""
        result = self.cursor.execute(q, (user_id,)).fetchone()
        if result is None:
            return None
        (id, ping_status, doctor_id, last_seen, limit_days) = result
        timestamp = datetime.datetime.fromisoformat(last_seen)
        return DbUser(
            id=id,
            ping_status=ping_status,
            doctor_id=doctor_id,
            last_seen=timestamp,
            limit_days=limit_days,
        )

    def add_doctor(self, doctor: DbDoctorToCreate) -> str:
        """
        Добавление доктора в базу данных
        Args:
            doctor (DbDoctorToCreate): объект доктора
        Returns:
            str: id доктора
        """
        q = """
        INSERT OR IGNORE INTO doctors
        (id, districtId, lpuId, specialtyId, doctorId)
        values (?, ?, ?, ?, ?)
        """
        id = self.__class__.get_doctor_hash(doctor)
        self.cursor.execute(
            q,
            (
                id,
                doctor.districtId,
                doctor.lpuId,
                doctor.specialtyId,
                doctor.doctorId,
            ),
        )
        self.connection.commit()
        return id

    def get_doctor(self, doctor_id: str) -> DbDoctor | None:
        """
        Получение доктора из базы данных
        Args:
            doctor_id: str - ид доктора в БД
        Returns:
            DbDoctor | None: объект доктора
        """
        q = """
        SELECT
            id,
            districtId,
            lpuId,
            specialtyId,
            doctorId
        FROM doctors
        WHERE doctors.id = ?;
        """
        self.cursor.execute(q, (doctor_id,))
        result = self.cursor.fetchone()
        if result is None:
            return None
        (id, districtId, lpuId, specialtyId, doctorId) = result
        return DbDoctor(
            id=id,
            districtId=districtId,
            lpuId=lpuId,
            specialtyId=specialtyId,
            doctorId=doctorId,
        )

    def get_user_ping_status(self, user_id: int) -> bool:
        """
        Получение флага активности проверки доктора
        Args:
            user_id: int - id пользователя
        Returns:
            bool: флаг активности проверки доктора
        """
        if not isinstance(user_id, int):
            raise TypeError("user_id must be int")
        q = """
        SELECT
            users.ping_status
        FROM users
        WHERE users.id = ?;
        """
        self.cursor.execute(q, (user_id,))
        result = self.cursor.fetchone()[0]
        return bool(result)

    def set_user_ping_status(self, user_id: int, ping_status: bool) -> None:
        """
        Устанавливает значение ping_status для пользователя с user_id
        Args:
            user_id: int - id пользователя
            ping_status: bool - флаг активности проверки доктора
        Returns:
            None: None
        """
        q = """
        UPDATE users
            set ping_status = ?
            WHERE users.id = ?;
        """
        self.cursor.execute(q, (ping_status, user_id))
        self.connection.commit()

    def add_user_doctor(self, user_id: int, doctor_id: str) -> None:
        """
        Добавляет доктора к пользователю
        Args:
            user_id: int - id пользователя
            doctor_id: str - id доктора
        Returns:
            None: None
        """
        q = """UPDATE users set doctor_id = ? where id = ?;"""
        self.cursor.execute(q, (doctor_id, user_id))
        self.connection.commit()

    def get_user_doctor(self, user_id: int) -> DbDoctor | None:
        """
        Возвращает доктора пользователя или None, если доктора нет.
        Args:
            user_id: int - id пользователя
        Returns:
            DbDoctor | None: объект доктора или None
        """
        q = """
        SELECT
            doctors.id,
            doctors.districtId,
            doctors.lpuId,
            doctors.specialtyId,
            doctors.doctorId
        FROM doctors
        WHERE
            doctors.id == (SELECT doctor_id FROM users WHERE id == ?)
        ;
        """
        self.cursor.execute(q, (user_id,))
        result = self.cursor.fetchone()
        if result is None:
            return None
        (id, districtId, lpuId, specialtyId, doctorId) = result
        doctor = DbDoctor(
            id=id,
            districtId=districtId,
            lpuId=lpuId,
            specialtyId=specialtyId,
            doctorId=doctorId,
        )
        return doctor

    def delete_user(self, user_id: int) -> None:
        """
        Удаляет пользователя из базы данных
        Args:
            user_id: int - id пользователя
        Returns:
            None: None
        """
        q = """DELETE FROM users WHERE id = ?"""
        self.cursor.execute(q, (user_id,))
        self.connection.commit()

    def update_user_time(
        self, user_id: int, last_seen: datetime.datetime | None = None
    ):
        """
        Обновляет время последней активности пользователя
        Args:
            user_id: int - id пользователя
            last_seen: datetime.datetime | None - время последней активности
        Returns
            None: None
        """
        if last_seen is None:
            last_seen = datetime.datetime.now(datetime.UTC)
        q = """ UPDATE users SET last_seen = ? WHERE id = ?;"""
        self.cursor.execute(q, (last_seen, user_id))
        self.connection.commit()

    def get_active_doctors(self) -> list[DbDoctor]:
        """
        Вернет список докторов, которых пингуют пользователи
        Args:
            None: None
        Returns:
            list[DbDoctor]: список докторов
        """
        q = """
        SELECT
            doctors.id,
            doctors.districtId,
            doctors.lpuId,
            doctors.specialtyId,
            doctors.doctorId
        FROM doctors
        WHERE doctors.id IN (
            SELECT users.doctor_id FROM users WHERE ping_status == 1
        );
        """
        self.cursor.execute(q)
        results = self.cursor.fetchall()
        doctors: list[DbDoctor] = [
            DbDoctor(
                id=d[0],
                districtId=d[1],
                lpuId=d[2],
                specialtyId=d[3],
                doctorId=d[4],
            )
            for d in results
        ]
        return doctors

    def get_users_by_doctor(self, doctor_id: str) -> list[DbUser]:
        """
        Возвращает список пользователей, которые привязаны к доктору
        Args:
            doctor_id: str - id доктора
        Returns:
            list[DbUser]: список пользователей
        """
        q = """
            SELECT
                users.id,
                users.ping_status,
                users.doctor_id,
                users.last_seen,
                users.limit_days
            FROM users
            WHERE users.doctor_id == ?;
        """
        self.cursor.execute(q, (doctor_id,))
        results = self.cursor.fetchall()
        users = [
            DbUser(
                id=d[0],
                ping_status=d[1],
                doctor_id=d[2],
                last_seen=d[3],
                limit_days=d[4],
            )
            for d in results
        ]
        return users

    def set_limit_days(self, user_id: int, limit_days: int | None):
        """Устанавливает кол-во дней для поиска"""
        q = """UPDATE users SET limit_days = ? WHERE id = ?;"""
        self.cursor.execute(q, (limit_days, user_id))
        self.connection.commit()

    def reset_limit_days(self, user_id: int):
        """Сбрасывает счётчик дней"""
        q = """UPDATE users SET limit_days = NULL WHERE id = ?;"""
        self.cursor.execute(q, (user_id,))
        self.connection.commit()
