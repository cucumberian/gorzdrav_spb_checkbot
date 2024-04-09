import datetime
from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy import delete
from db.database import sync_engine
from db.database import sync_session_factory
from db.database import Base
import db.models as db_models


class SyncOrm:
    @staticmethod
    def create_tables():
        # Base.metadata.drop_all(bind=sync_engine)
        Base.metadata.create_all(bind=sync_engine)

    @staticmethod
    def add_user(user_id: int):
        with sync_session_factory() as session:
            user = db_models.UserOrm(
                id=user_id,
            )
            print("user =", user)
            session.add(user)
            session.commit()

    def update_user(
        user_id: int,
        ping_status: bool | None = None,
        doctor_id: int | None = None,
    ):
        with sync_session_factory() as session:
            user = session.query(db_models.UserOrm).filter(
                db_models.UserOrm.id == user_id
            )
            if ping_status is not None:
                user.update({"ping_status": ping_status})
            if doctor_id is not None:
                user.update({"doctor_id": doctor_id})
            user.update({"last_seen": datetime.datetime.now(datetime.UTC)})
            session.commit()

    @staticmethod
    def delete_user(user_id: int):
        with sync_session_factory() as session:
            stmt = text("DELETE FROM users WHERE id = :id")
            session.execute(stmt, {"id": user_id})
            session.commit()

    @staticmethod
    def get_user_doctor(user_id: int) -> db_models.DoctorOrm | None:
        with sync_session_factory() as session:
            user = session.get(db_models.UserOrm, {"id": user_id})
            if not user:
                return None
            doctor = session.get(db_models.DoctorOrm, {"id": user.doctor_id})
            return doctor

    @staticmethod
    def get_user(user_id: int) -> db_models.UserOrm | None:
        """
        Получает из БД информацию о пользователе
        :param user_id: int - ид пользователя
        :return: db_models.UserOrm | None - модель пользователя
        """
        with sync_session_factory() as session:
            user = session.get(db_models.UserOrm, {"id": user_id})
            return user

    @staticmethod
    def get_users(**filter) -> list[db_models.UserOrm]:
        with sync_session_factory() as session:
            users = session.query(db_models.UserOrm).filter_by(**filter).all()
            return users

    @staticmethod
    def add_doctor(lpuId: int, specialtyId: str, doctorId: str) -> str:
        """
        Добавляет в БД доктора
        :param lpuId: int - ид медучреждения по апи
        :param specialtyId: str - ид специальности по апи
        :param doctorId: str - ид доктора по апи
        :return: id: str доктора в базе данных
        """

        with sync_session_factory() as session:
            doctor_id = f"{lpuId}_{specialtyId}_{doctorId}"
            doctor = session.query(db_models.DoctorOrm).get(doctor_id)
            if not doctor:
                doctor: db_models.DoctorOrm = db_models.DoctorOrm(
                    id=doctor_id,
                    lpuId=lpuId,
                    specialtyId=specialtyId,
                    doctorId=doctorId,
                )
                session.add(doctor)
                session.commit()
                doctor_id = doctor.id
        return doctor_id

    @staticmethod
    def get_pinged_doctors() -> list[db_models.DoctorOrm]:
        """
        Получает список докторов, которых нужно опросить для статуса талонов
        :return: list[db_models.DoctorOrm] - список докторов
        """
        with sync_session_factory() as session:
            doctors = (
                session.query(db_models.DoctorOrm)
                .join(db_models.UserOrm)
                .filter(db_models.UserOrm.ping_status == True)
                .all()
            )
            return doctors
