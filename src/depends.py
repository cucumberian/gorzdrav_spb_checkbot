from config import Config
from db.sqlite_db import SqliteDb

sqlite_db = SqliteDb(db_path=Config.DB_FILE)
