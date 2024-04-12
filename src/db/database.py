from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

from config import Config

sync_engine = create_engine(Config.dsn_string, echo=False)

sync_session_factory = sessionmaker(bind=sync_engine)


class Base(DeclarativeBase):
    pass

