import datetime

class SqliteDb:
    def __init__(self, file='sqlite.db'):
        self.file = file
        self.connection = __import__('sqlite3').connect(database=self.file,  check_same_thread=False, timeout=5)
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
        q = """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            is_active_ping BOOLEAN DEFAULT 0,
            doctor_id varchar(40),
            last_seen_datetime DATETIME,
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        );"""
        self.cursor.execute(q)
        self.connection.commit()

    def create_table_doctors(self) -> None:
        q = """CREATE TABLE IF NOT EXISTS doctors (
            id VARCHAR(40) PRIMARY KEY,
            doctor_id INTEGER REQUIRED,
            speciality_id INTEGER REQUIRED,
            hospital_id INTEGER REQUIRED
        );"""
        self.cursor.execute(q)
        self.connection.commit()
    
    def add_user(self, user_id: int, datetime=datetime.datetime.now()) -> None:
        q = """INSERT OR IGNORE INTO USERS (id, last_seen_datetime) values (?, ?)"""
        self.cursor.execute(q, (user_id, datetime))
        self.connection.commit()
    
    def add_doctor(self, doctor_id, speciality_id, hospital_id: int) -> str:
        print(f"{doctor_id = } {speciality_id = } {hospital_id = }")
        q = """INSERT OR IGNORE INTO doctors (id, doctor_id, speciality_id, hospital_id) values (?, ?, ?, ?)"""
        id = f"{hospital_id}_{speciality_id}_{doctor_id}"
        self.cursor.execute(q, (id, doctor_id, speciality_id, hospital_id))
        self.connection.commit()
        return id
    
    def get_user_ping_status(self, user_id: int) -> bool:
        q = """
        SELECT
            id
        FROM users
        WHERE users.id = ?;
        """
        self.cursor.execute(q, (user_id, ))
        result = self.cursor.fetchone()
        return bool(result)

    def _set_user_ping_status(self, user_id: int, status: int=0) -> None:
        q = """
        UPDATE users 
            set is_active_ping = ? 
            WHERE users.id = ?;
        """
        self.cursor.execute(q, (status, user_id))
        self.connection.commit()

    def set_user_ping(self, user_id: int) -> None:
        self._set_user_ping_status(user_id, 1)
    
    def clear_user_ping(self, user_id: int) -> None:
        self._set_user_ping_status(user_id, 0)
    
    def add_user_doctor(self, user_id: int, doctor_id: str) -> None:
        q = """ UPDATE users set doctor_id = ? where id = ?;"""
        self.cursor.execute(q, (doctor_id, user_id))
        self.connection.commit()

    def del_user(self, user_id: int) -> None:
        q = """ DELETE FROM users WHERE id = ?"""
        self.cursor.execute(q, (user_id, ))
        self.connection.commit()
        
    def update_user_time(self, user_id: int, datetime=datetime.datetime.now()):
        q = """ UPDATE users SET last_seen_datetime = ? WHERE id = ?;"""
        self.cursor.execute(q, (datetime, user_id, ))
        self.connection.commit()
    
    def get_user_doctor(self, user_id: int):
        """
        Return (hostpital_id, speciality_id, doctor_id)
        """
        q = """
        SELECT 
            doctors.hospital_id,
            doctors.speciality_id,
            doctors.doctor_id
        FROM doctors
        WHERE 
                doctors.id == (SELECT doctor_id FROM users WHERE id == ?)
        ;
        """
        self.cursor.execute(q, (user_id, ))
        result = self.cursor.fetchone()
        try:
            return {'hospital_id': result[0], 'speciality_id': result[1], 'doctor_id': result[2]}
        except:
            return None
    
    def get_active_doctors(self) -> list:
        """
        Return active doctors (hospital_id, speciality_id, doctor_id) 
        (doctors pinged by user)
        """
        q = """
            SELECT
                doctors.hospital_id,
                doctors.speciality_id,
                doctors.doctor_id
            from doctors
            where doctors.id in (select users.doctor_id from users where is_active_ping == True);
        """
        self.cursor.execute(q)
        results = self.cursor.fetchall()
        return [
            {
                'hospital_id': r[0], 
                'speciality_id': r[1], 
                'doctor_id': r[2]
            }
            for r in results
        ]
    
    def get_users_by_doctor(self, doctor_id: str) -> list:
        q = """
            SELECT 
                users.id
            FROM users
            WHERE users.doctor_id == ?;
        """
        self.cursor.execute(q, (doctor_id, ))
        results = self.cursor.fetchall()
        return results
